document.addEventListener('DOMContentLoaded', function () {
    'use strict';

    /* ---- Conditional fields: event type "other" ---- */
    var eventTypeField = document.getElementById('id_event_type');
    var otherTypeRow = document.getElementById('other-type-row');

    function toggleOtherType() {
        if (eventTypeField && otherTypeRow) {
            var show = eventTypeField.value === 'other';
            otherTypeRow.style.display = show ? 'flex' : 'none';
            if (show) otherTypeRow.classList.add('animate-slide-down');
        }
    }

    if (eventTypeField) {
        eventTypeField.addEventListener('change', toggleOtherType);
        toggleOtherType();
    }

    /* ---- Conditional fields: RSVP status radios ---- */
    var statusRadios = document.querySelectorAll('input[name="status"]');
    var confirmedFields = document.getElementById('confirmed-fields');

    function toggleConfirmedFields() {
        if (!statusRadios.length || !confirmedFields) return;
        var confirmed = Array.from(statusRadios).some(function (r) { return r.checked && r.value === 'confirmed'; });
        confirmedFields.style.display = confirmed ? 'block' : 'none';
        if (confirmed) confirmedFields.classList.add('animate-slide-down');
    }

    if (statusRadios.length && confirmedFields) {
        statusRadios.forEach(function (r) { r.addEventListener('change', toggleConfirmedFields); });
        toggleConfirmedFields();
    }

    /* ---- Conditional fields: drink "other" ---- */
    function setupDrinkOther(selectId, otherId) {
        var select = document.getElementById(selectId);
        var other = document.getElementById(otherId);
        if (!select || !other) return;

        function toggle() {
            var show = select.value === 'other';
            other.style.display = show ? 'block' : 'none';
            if (show) other.classList.add('animate-slide-down');
        }
        select.addEventListener('change', toggle);
        toggle();
    }

    setupDrinkOther('id_drink_choice', 'drink-other-field');
    setupDrinkOther('id_companion_drink_choice', 'companion-drink-other-field');

    /* ---- Conditional fields: companion ---- */
    var isAccompanied = document.getElementById('id_is_accompanied');
    var companionFields = document.getElementById('companion-fields');

    function toggleCompanionFields() {
        if (!isAccompanied || !companionFields) return;
        var show = isAccompanied.checked;
        companionFields.style.display = show ? 'block' : 'none';
        if (show) companionFields.classList.add('animate-slide-down');
    }

    if (isAccompanied && companionFields) {
        isAccompanied.addEventListener('change', toggleCompanionFields);
        toggleCompanionFields();
    }

    /* ---- Staggered fade-in for cards ---- */
    var cards = document.querySelectorAll('.card');
    cards.forEach(function (card, i) {
        card.style.opacity = '0';
        card.classList.add('animate-fade-in-up');
        card.style.animationDelay = (i * 0.08) + 's';
        card.style.opacity = '1';
    });

    /* ---- Animated stat counters ---- */
    var statValues = document.querySelectorAll('.stat-value');
    statValues.forEach(function (el) {
        var target = parseInt(el.textContent, 10);
        if (isNaN(target)) return;
        var duration = 800;
        var steps = 30;
        var stepTime = duration / steps;
        var increment = target / steps;
        var current = 0;
        el.textContent = '0';
        el.classList.add('animate-count');

        function animateStep() {
            current += increment;
            if (current >= target) {
                el.textContent = target;
                return;
            }
            el.textContent = Math.round(current);
            setTimeout(animateStep, stepTime);
        }

        var observer = new IntersectionObserver(function (entries) {
            entries.forEach(function (entry) {
                if (entry.isIntersecting) {
                    setTimeout(animateStep, 200);
                    observer.unobserve(el);
                }
            });
        }, { threshold: 0.5 });
        observer.observe(el);
    });

    /* ---- RSVP radio card style ---- */
    var radioCards = document.querySelectorAll('.rsvp-radio-card');
    radioCards.forEach(function (card) {
        var radio = card.querySelector('input[type="radio"]');
        if (!radio) return;
        if (radio.checked) card.classList.add('selected');
        radio.addEventListener('change', function () {
            radioCards.forEach(function (c) { c.classList.remove('selected'); });
            if (this.checked) card.classList.add('selected');
        });
    });
});

/* ---- Copy RSVP link to clipboard ---- */
function copyRSVPLink(elementId) {
    var input = document.getElementById(elementId);
    if (!input) return;

    input.select();
    input.setSelectionRange(0, 99999);

    navigator.clipboard.writeText(input.value).then(function () {
        var btn = input.nextElementSibling;
        if (!btn) return;
        var original = btn.innerHTML;
        btn.innerHTML = '<i class="bi bi-check-lg"></i>';
        setTimeout(function () { btn.innerHTML = original; }, 2000);
    });
}
