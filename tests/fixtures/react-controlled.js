(function () {
  const root = ReactDOM.createRoot(document.getElementById("react-root"));
  function ControlledUsername() {
    const [value, setValue] = React.useState("");
    window.reactUsernameState = value;
    return React.createElement(
      "section",
      null,
      React.createElement("h2", null, "React controlled profile"),
      React.createElement("label", { htmlFor: "react-username" }, "Display nickname"),
      React.createElement("input", {
        id: "react-username",
        name: "nickname",
        value,
        placeholder: "React controlled value",
        onChange: (event) => setValue(event.target.value),
      }),
      React.createElement("p", { id: "react-value" }, "React state: " + value),
    );
  }
  root.render(React.createElement(ControlledUsername));
})();
