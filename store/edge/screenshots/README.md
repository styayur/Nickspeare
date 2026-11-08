# Edge store screenshots

These listing images are composited from real Microsoft Edge captures of the packaged extension and the public review fixture; the extension UI itself is not mocked. Regenerate them with:

```sh
npm run build:extension:test
python scripts/capture_edge_store_screenshots.py
```

Final listing assets:

1. `01-generate.png` — generated candidates in the Nickspeare popup.
2. `02-shape.png` — advanced username controls and regenerated candidates.
3. `03-fill-field.png` — explicit field selection with sensitive fields excluded.

All files are exactly **1280 × 800** PNGs. `capture-report.json` records the browser and the real-capture source used for the composition.
