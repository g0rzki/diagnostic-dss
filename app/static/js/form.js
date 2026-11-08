const form = document.querySelector("form");

function currentValue(name) {
  const checked = form.querySelector(`input[name="${name}"]:checked`);
  if (checked) {
    return checked.value;
  }
  const input = form.querySelector(`input[name="${name}"][type="text"]`);
  return input ? input.value.trim() : "";
}

function conditionMet(block) {
  const value = currentValue(block.dataset.showParam);
  switch (block.dataset.showOp) {
    case "podano":
      return value !== "";
    case "=":
      return value === block.dataset.showValue;
    default:
      return value !== block.dataset.showValue;
  }
}

function updateConditionalFields() {
  for (const block of form.querySelectorAll("[data-show-param]")) {
    block.hidden = !conditionMet(block);
  }
}

form.addEventListener("input", updateConditionalFields);
updateConditionalFields();
