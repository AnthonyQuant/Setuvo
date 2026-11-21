/**
 * static/js/setuvo.js
 *
 * Unobtrusive progressive enhancement for Setuvo:
 * - Mobile navigation toggle & dismissible flash messages
 * - Auto-submitting sort and delivery-zone selectors
 * - Multi-product quick-compare floating bar on /catalogue
 * - Live client-side Naira (₦) budget tracking on /setup-builder
 * - Live kit discount recalculation on /bundles
 * - Live Nigerian delivery fee & grand total preview on /checkout
 */

(function () {
  "use strict";

  function formatNaira(amount) {
    const num = Number.isFinite(Number(amount)) ? Number(amount) : 0;
    return (
      "₦" +
      num.toLocaleString("en-NG", {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2,
      })
    );
  }

  /* ------------------------------------------------------------------------
     1. Mobile Navigation Toggle
     ------------------------------------------------------------------------ */
  function initMobileNav() {
    const toggleBtn = document.getElementById("mobile-nav-toggle");
    const primaryNav = document.getElementById("primary-nav");
    if (!toggleBtn || !primaryNav) return;

    toggleBtn.addEventListener("click", function () {
      const isOpen = primaryNav.classList.toggle("open");
      toggleBtn.setAttribute("aria-expanded", String(isOpen));
    });
  }

  /* ------------------------------------------------------------------------
     2. Dismissible Flash Banners
     ------------------------------------------------------------------------ */
  function initFlashDismiss() {
    document.querySelectorAll(".flash-close").forEach(function (btn) {
      btn.addEventListener("click", function () {
        const alertBox = btn.closest(".flash-alert");
        if (alertBox) {
          alertBox.remove();
        }
      });
    });
  }

  /* ------------------------------------------------------------------------
     3. Auto-Submitting Sort & Delivery Zone Dropdowns
     ------------------------------------------------------------------------ */
  function initAutoSubmitSelects() {
    document
      .querySelectorAll('select[data-auto-submit="true"]')
      .forEach(function (selectEl) {
        selectEl.addEventListener("change", function () {
          if (selectEl.form) {
            selectEl.form.submit();
          }
        });
      });
  }

  /* ------------------------------------------------------------------------
     4. Catalogue Quick-Compare Multi-Checkbox Bar (2–3 Products)
     ------------------------------------------------------------------------ */
  function initQuickCompareBar() {
    const checkboxes = Array.from(
      document.querySelectorAll(".compare-select-checkbox")
    );
    const bar = document.getElementById("compare-selection-bar");
    const statusText = document.getElementById("compare-bar-status");
    const clearBtn = document.getElementById("compare-clear-btn");
    const launchBtn = document.getElementById("compare-launch-btn");

    if (!checkboxes.length || !bar || !statusText || !launchBtn) return;

    const baseCompareHref = launchBtn.getAttribute("href") || "/compare";

    function syncCompareBar(changedCheckbox) {
      const checked = checkboxes.filter(function (cb) {
        return cb.checked;
      });

      if (checked.length > 3 && changedCheckbox) {
        changedCheckbox.checked = false;
        statusText.textContent =
          "Maximum 3 products can be compared side-by-side.";
        return;
      }

      if (checked.length === 0) {
        bar.hidden = true;
        return;
      }

      bar.hidden = false;
      const ids = checked.map(function (cb) {
        return cb.value;
      });

      if (checked.length === 1) {
        statusText.textContent =
          "1 product selected — pick 1 or 2 more to compare side-by-side.";
        launchBtn.setAttribute("href", baseCompareHref + "?product_1=" + ids[0]);
      } else {
        statusText.textContent =
          checked.length + " products selected for side-by-side comparison.";
        launchBtn.setAttribute("href", baseCompareHref + "?ids=" + ids.join(","));
      }
    }

    checkboxes.forEach(function (cb) {
      cb.addEventListener("change", function () {
        syncCompareBar(cb);
      });
    });

    if (clearBtn) {
      clearBtn.addEventListener("click", function () {
        checkboxes.forEach(function (cb) {
          cb.checked = false;
        });
        syncCompareBar(null);
      });
    }
  }

  /* ------------------------------------------------------------------------
     5. Workstation Setup Builder Live Naira Budget Recalculation
     ------------------------------------------------------------------------ */
  function initSetupBuilderLiveBudget() {
    const form = document.getElementById("setup-builder-form");
    const budgetInput = document.getElementById("setup-budget");
    const panel = document.getElementById("setup-budget-panel");
    const itemCheckboxes = Array.from(
      document.querySelectorAll(".setup-item-checkbox")
    );

    if (!form || !budgetInput || !panel || !itemCheckboxes.length) return;

    const warningBox = document.getElementById("setup-budget-warning");
    const utilText = document.getElementById("setup-utilization-text");
    const utilBar = document.getElementById("setup-utilization-bar");
    const targetEl = document.getElementById("summary-target-budget");
    const countEl = document.getElementById("summary-selected-count");
    const totalEl = document.getElementById("summary-selected-total");
    const remLabelEl = document.getElementById("summary-remaining-label");
    const remAmountEl = document.getElementById("summary-remaining-amount");

    function updateSetupSummary() {
      const rawBudget = parseFloat(budgetInput.value);
      const budget = Number.isFinite(rawBudget) && rawBudget > 0 ? rawBudget : 0;

      let total = 0;
      let count = 0;
      const selectedItems = [];

      itemCheckboxes.forEach(function (cb) {
        const row = cb.closest(".setup-product-row");
        if (cb.checked) {
          const price = parseFloat(cb.dataset.price || "0") || 0;
          const name = cb.dataset.name || "Selected Item";
          total += price;
          count += 1;
          selectedItems.push({ name: name, price: price });
          if (row) row.classList.add("selected");
        } else if (row) {
          row.classList.remove("selected");
        }
      });

      const pct = budget > 0 ? Math.round((total / budget) * 1000) / 10 : 0;
      const isOver = budget > 0 && total > budget;
      const diff = Math.abs(budget - total);

      if (targetEl) targetEl.textContent = formatNaira(budget);
      if (countEl) countEl.textContent = String(count);
      if (totalEl) totalEl.textContent = formatNaira(total);
      if (utilText) utilText.textContent = pct + "%";

      if (utilBar) {
        utilBar.style.width = Math.min(100, Math.max(0, pct)) + "%";
        utilBar.classList.toggle("over-budget", isOver);
      }

      if (remLabelEl && remAmountEl) {
        if (isOver) {
          remLabelEl.textContent = "Over Budget By";
          remAmountEl.textContent = "-" + formatNaira(diff);
          remAmountEl.classList.remove("text-success");
          remAmountEl.classList.add("text-danger");
        } else {
          remLabelEl.textContent = "Remaining Budget";
          remAmountEl.textContent = formatNaira(diff);
          remAmountEl.classList.remove("text-danger");
          remAmountEl.classList.add("text-success");
        }
      }

      if (warningBox) {
        if (isOver) {
          warningBox.hidden = false;
          const strongEl = warningBox.querySelector("strong");
          const pEl = warningBox.querySelector("p");
          if (strongEl) {
            strongEl.textContent = "Budget Exceeded by " + formatNaira(diff);
          }
          if (pEl) {
            pEl.textContent =
              "Your selected gear (" +
              formatNaira(total) +
              ") exceeds your " +
              formatNaira(budget) +
              " target budget.";
          }
        } else {
          warningBox.hidden = true;
        }
      }

      const selectedContainer = panel.querySelector(".selected-setup-items");
      if (selectedContainer) {
        let listEl = document.getElementById("summary-selected-list");
        const emptyNote = document.getElementById("summary-empty-note");

        if (selectedItems.length > 0) {
          if (emptyNote) emptyNote.hidden = true;
          if (!listEl) {
            listEl = document.createElement("ul");
            listEl.id = "summary-selected-list";
            listEl.className = "mini-selected-list";
            selectedContainer.appendChild(listEl);
          }
          listEl.hidden = false;
          listEl.innerHTML = selectedItems
            .map(function (item) {
              return (
                "<li><span>" +
                escapeHtml(item.name) +
                "</span><strong>" +
                formatNaira(item.price) +
                "</strong></li>"
              );
            })
            .join("");
        } else {
          if (listEl) listEl.hidden = true;
          if (emptyNote) emptyNote.hidden = false;
        }
      }
    }

    itemCheckboxes.forEach(function (cb) {
      cb.addEventListener("change", updateSetupSummary);
    });
    budgetInput.addEventListener("input", updateSetupSummary);
  }

  /* ------------------------------------------------------------------------
     6. Preconfigured Bundles Live Discount Recalculation
     ------------------------------------------------------------------------ */
  function initBundleLivePricing() {
    document.querySelectorAll(".bundle-detail-card").forEach(function (card) {
      const discountPct = parseFloat(card.dataset.discountPct || "0") || 0;
      const checkboxes = Array.from(
        card.querySelectorAll(".bundle-item-checkbox")
      );
      if (!checkboxes.length) return;

      const individualEl = card.querySelector("[data-bundle-individual]");
      const discountEl = card.querySelector("[data-bundle-discount-amt]");
      const totalEl = card.querySelector("[data-bundle-total]");
      const finalEl = card.querySelector("[data-bundle-final]");
      const savingsEl = card.querySelector("[data-bundle-savings]");

      function recalculateBundle() {
        let individualSum = 0;
        let checkedCount = 0;

        checkboxes.forEach(function (cb) {
          if (cb.checked) {
            const price = parseFloat(cb.dataset.price || "0") || 0;
            const qty = parseInt(cb.dataset.quantity || "1", 10) || 1;
            individualSum += price * qty;
            checkedCount += 1;
          }
        });

        const effectiveDiscountPct = checkedCount >= 2 ? discountPct : 0;
        const discountAmt =
          Math.round(individualSum * (effectiveDiscountPct / 100) * 100) / 100;
        const finalTotal = Math.max(0, individualSum - discountAmt);

        if (individualEl) individualEl.textContent = formatNaira(individualSum);
        if (discountEl) discountEl.textContent = "-" + formatNaira(discountAmt);
        if (totalEl) totalEl.textContent = formatNaira(finalTotal);
        if (finalEl) finalEl.textContent = formatNaira(finalTotal);
        if (savingsEl) {
          if (checkedCount >= 2 && discountAmt > 0) {
            savingsEl.textContent =
              "You save " +
              formatNaira(discountAmt) +
              " vs. buying separately";
          } else if (checkedCount === 1) {
            savingsEl.textContent =
              "Select at least 2 kit items to unlock the " +
              Math.round(discountPct) +
              "% bundle discount";
          } else {
            savingsEl.textContent = "Select at least 1 component to add";
          }
        }
      }

      checkboxes.forEach(function (cb) {
        cb.addEventListener("change", recalculateBundle);
      });
    });
  }

  /* ------------------------------------------------------------------------
     7. Guest Checkout Live Delivery Zone Fee & Grand Total Preview
     ------------------------------------------------------------------------ */
  function initCheckoutZonePreview() {
    const zoneSelect = document.getElementById("checkout_delivery_zone");
    const summaryCard = document.getElementById("checkout-summary-card");
    const checkoutForm = document.getElementById("guest-checkout-form");

    if (checkoutForm) {
      checkoutForm.addEventListener("submit", function () {
        const submitBtn = checkoutForm.querySelector('button[type="submit"]');
        if (submitBtn && !submitBtn.disabled) {
          submitBtn.disabled = true;
          submitBtn.textContent = "Placing Order...";
        }
      });
    }

    if (!zoneSelect || !summaryCard) return;

    const subtotal = parseFloat(summaryCard.dataset.subtotal || "0") || 0;
    const labelEl = document.getElementById("checkout-zone-label");
    const feeEl = document.getElementById("checkout-delivery-fee");
    const etaEl = document.getElementById("checkout-delivery-eta");
    const grandTotalEl = document.getElementById("checkout-grand-total");
    const btnTotalEl = document.getElementById("checkout-btn-total");

    function updateCheckoutTotals() {
      const selectedOption = zoneSelect.options[zoneSelect.selectedIndex];
      if (!selectedOption) return;

      const fee = parseFloat(selectedOption.dataset.fee || "0") || 0;
      const eta = selectedOption.dataset.eta || "";
      const label = selectedOption.dataset.label || "";
      const grandTotal = subtotal + fee;

      if (labelEl && label) labelEl.textContent = label;
      if (feeEl) feeEl.textContent = fee === 0 ? "Free" : formatNaira(fee);
      if (etaEl && eta) etaEl.textContent = eta;
      if (grandTotalEl) grandTotalEl.textContent = formatNaira(grandTotal);
      if (btnTotalEl) btnTotalEl.textContent = formatNaira(grandTotal);
    }

    zoneSelect.addEventListener("change", updateCheckoutTotals);
  }

  function escapeHtml(text) {
    const div = document.createElement("div");
    div.textContent = text;
    return div.innerHTML;
  }

  document.addEventListener("DOMContentLoaded", function () {
    initMobileNav();
    initFlashDismiss();
    initAutoSubmitSelects();
    initQuickCompareBar();
    initSetupBuilderLiveBudget();
    initBundleLivePricing();
    initCheckoutZonePreview();
  });
})();