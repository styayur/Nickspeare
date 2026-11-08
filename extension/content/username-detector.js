(() => {
  if (globalThis.__nickspeareFieldBridgeInstalled) return;
  globalThis.__nickspeareFieldBridgeInstalled = true;

  const registry = new Map();
  let nextFieldId = 1;
  const USERNAME_HINTS = /(user[\s_-]*name|username|handle|nickname|nick[\s_-]*name|display[\s_-]*name|screen[\s_-]*name|account[\s_-]*name|profile[\s_-]*name)/i;
  const NICKNAME_HINTS = /(nickname|nick[\s_-]*name|display[\s_-]*name|profile[\s_-]*name)/i;
  const REGISTER_HINTS = /(sign[\s_-]*up|register|registration|create[\s_-]*account|join now|new account|choose a username)/i;
  const LOGIN_HINTS = /(sign[\s_-]*in|log[\s_-]*in|login|welcome back|current password)/i;
  const SENSITIVE_HINTS = /(password|passcode|passwd|one[\s_-]*time|otp|verification code|credit card|card number|security code|cvv|cvc|ssn|social security|iban|routing number|bank|payment|billing|email|e-mail)/i;
  const ALLOWED_TYPES = new Set(['text', 'search']);
  const MAX_FIELDS = 20;

  const text = (value, limit = 140) => String(value || '').replace(/\s+/g, ' ').trim().slice(0, limit);

  function isVisible(element) {
    if (!(element instanceof HTMLElement)) return false;
    if (element.hidden || element.getAttribute('aria-hidden') === 'true') return false;
    const style = getComputedStyle(element);
    if (style.display === 'none' || style.visibility === 'hidden' || Number(style.opacity) === 0) return false;
    const rect = element.getBoundingClientRect();
    return rect.width > 2 && rect.height > 2;
  }

  function labelText(element) {
    const values = [];
    for (const label of element.labels || []) values.push(label.textContent || '');
    const wrapping = element.closest('label');
    if (wrapping) values.push(wrapping.textContent || '');
    const labelledby = element.getAttribute('aria-labelledby');
    if (labelledby) {
      for (const id of labelledby.split(/\s+/)) {
        const node = id ? document.getElementById(id) : null;
        if (node) values.push(node.textContent || '');
      }
    }
    return text(values.join(' '));
  }

  function contextText(element) {
    const pieces = [];
    const form = element.form || element.closest('form');
    if (form) {
      pieces.push(form.id, form.name, form.getAttribute('aria-label'), form.getAttribute('action'));
      const heading = form.querySelector('h1, h2, h3, legend, [role="heading"]');
      if (heading) pieces.push(heading.textContent);
    }
    const fieldset = element.closest('fieldset');
    if (fieldset) pieces.push(fieldset.textContent?.slice(0, 240));
    return text(pieces.filter(Boolean).join(' '), 320);
  }

  function isEditable(element) {
    return !element.disabled && !element.readOnly && element.getAttribute('aria-disabled') !== 'true';
  }

  function describe(element) {
    if (!(element instanceof HTMLInputElement || element instanceof HTMLTextAreaElement)) return null;
    const type = element instanceof HTMLInputElement ? (element.type || 'text').toLowerCase() : 'textarea';
    if (!ALLOWED_TYPES.has(type) && type !== 'textarea') return null;
    if (!isVisible(element) || !isEditable(element)) return null;

    const label = labelText(element);
    const nearby = contextText(element);
    const autocomplete = text(element.getAttribute('autocomplete'), 40).toLowerCase();
    const local = text([
      element.id,
      element.name,
      element.placeholder,
      element.getAttribute('aria-label'),
      element.getAttribute('title'),
      label,
      element.getAttribute('data-testid'),
    ].filter(Boolean).join(' '), 320);
    const all = `${local} ${nearby}`;
    if (SENSITIVE_HINTS.test(all) || /^(email|password|tel|number|hidden)$/i.test(type)) return null;
    if (autocomplete.includes('password') || autocomplete.includes('email') || autocomplete.includes('one-time-code')) return null;

    const reasons = [];
    let score = 0;
    let category = 'other_text';
    if (USERNAME_HINTS.test(local)) {
      score += 7;
      category = 'registration_username';
      reasons.push('Field name or label mentions a username or handle');
    }
    if (NICKNAME_HINTS.test(local)) {
      score += 3;
      category = 'display_name';
      reasons.push('Field name or label mentions a display nickname');
    }
    if (autocomplete === 'username') {
      score += 5;
      reasons.push('autocomplete="username"');
    }
    const registerContext = REGISTER_HINTS.test(nearby);
    const loginContext = !registerContext && (LOGIN_HINTS.test(nearby) || Boolean(element.form?.querySelector('input[type="password"]')));
    if (registerContext) {
      score += 3;
      if (category !== 'display_name') category = 'registration_username';
      reasons.push('Registration context detected');
    }
    if (loginContext) {
      if (category !== 'display_name') category = 'login_username';
      score += 1;
      reasons.push('Login context detected; choose this field explicitly');
    }
    if (type === 'search') {
      score -= 3;
      reasons.push('Search field');
    }
    if (!reasons.length) reasons.push('Generic editable text field; low confidence');

    const confidence = score >= 9 ? 'high' : score >= 5 ? 'medium' : 'low';
    return {
      element,
      descriptor: {
        id: String(nextFieldId++),
        category,
        confidence,
        score,
        reasons: reasons.slice(0, 5),
        label: label || text(element.placeholder || element.getAttribute('aria-label') || element.name || element.id || `Text field ${nextFieldId - 1}`, 80),
        elementId: text(element.id, 60),
        name: text(element.name || element.id, 60),
        autocomplete,
        type,
        isEmpty: element.value.length === 0,
      },
    };
  }

  function scanFields() {
    registry.clear();
    nextFieldId = 1;
    const fields = [];
    let sensitiveSkipped = 0;
    let nonEditableSkipped = 0;
    for (const element of document.querySelectorAll('input, textarea')) {
      if (!(element instanceof HTMLInputElement || element instanceof HTMLTextAreaElement)) continue;
      const type = element instanceof HTMLInputElement ? (element.type || 'text').toLowerCase() : 'textarea';
      if (!ALLOWED_TYPES.has(type) && type !== 'textarea') {
        if (['email', 'password', 'tel', 'number', 'hidden'].includes(type)) sensitiveSkipped += 1;
        continue;
      }
      if (!isVisible(element) || !isEditable(element)) {
        nonEditableSkipped += 1;
        continue;
      }
      const record = describe(element);
      if (!record) {
        sensitiveSkipped += 1;
        continue;
      }
      if (fields.length >= MAX_FIELDS) break;
      registry.set(record.descriptor.id, record.element);
      fields.push(record.descriptor);
    }
    const order = { high: 0, medium: 1, low: 2 };
    fields.sort((a, b) => order[a.confidence] - order[b.confidence] || b.score - a.score || a.id.localeCompare(b.id));
    return {
      ok: true,
      fields,
      summary: {
        candidates: fields.length,
        sensitiveSkipped,
        nonEditableSkipped,
        crossFrameNote: 'Only the top-level page is inspected; fields inside iframes are not accessed.',
      },
    };
  }

  function setNativeValue(element, value) {
    const prototype = element instanceof HTMLTextAreaElement ? HTMLTextAreaElement.prototype : HTMLInputElement.prototype;
    const setter = Object.getOwnPropertyDescriptor(prototype, 'value')?.set;
    if (setter) setter.call(element, value);
    else element.value = value;
    element.dispatchEvent(new InputEvent('input', { bubbles: true, composed: true, inputType: 'insertText', data: value }));
    element.dispatchEvent(new Event('change', { bubbles: true, composed: true }));
    return element.value === value;
  }

  function fillField(message) {
    const fieldId = String(message.fieldId || '');
    const value = typeof message.value === 'string' ? message.value : '';
    const element = registry.get(fieldId);
    if (!element || !element.isConnected) return { ok: false, errorCode: 'FIELD_NOT_FOUND', message: 'The selected field is no longer available. Scan again.' };
    if (!/^[A-Za-z0-9_]{1,64}$/.test(value)) return { ok: false, errorCode: 'INVALID_VALUE', message: 'The username does not meet the insertion safety rules.' };
    if (!isVisible(element) || !isEditable(element)) return { ok: false, errorCode: 'FIELD_NOT_EDITABLE', message: 'The selected field is no longer editable.' };
    const current = describe(element);
    if (!current || SENSITIVE_HINTS.test(`${element.name} ${element.id} ${labelText(element)} ${element.type}`)) {
      return { ok: false, errorCode: 'SENSITIVE_FIELD', message: 'Sensitive fields are never filled.' };
    }
    if (element.value.length > 0 && message.replaceExisting !== true) {
      return { ok: false, errorCode: 'FIELD_NOT_EMPTY', message: 'This field already contains text. Use an explicit replace action.' };
    }
    const previous = element.value;
    const updated = setNativeValue(element, value);
    if (!updated) {
      if (previous) setNativeValue(element, previous);
      return { ok: false, errorCode: 'INSERTION_FAILED', message: 'The page did not accept the new value.' };
    }
    return { ok: true, value, label: current.descriptor.label, replacedExisting: previous.length > 0 };
  }

  chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
    if (!sender || sender.id !== chrome.runtime.id || !message || typeof message.type !== 'string') return false;
    if (message.type === 'nickspeare.scan-fields') {
      try {
        sendResponse(scanFields());
      } catch {
        sendResponse({ ok: false, errorCode: 'SCAN_FAILED', message: 'The page could not be inspected safely.' });
      }
      return false;
    }
    if (message.type === 'nickspeare.fill-field') {
      try {
        sendResponse(fillField(message));
      } catch {
        sendResponse({ ok: false, errorCode: 'INSERTION_FAILED', message: 'The page rejected the insertion.' });
      }
      return false;
    }
    return false;
  });
})();
