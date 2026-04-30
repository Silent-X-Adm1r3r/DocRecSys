/* ─── DocRecSys Chat Client — Enhanced ───────────────────────────── */

const SESSION_ID = crypto.randomUUID();
const WEBHOOK   = "/webhook";
const FEEDBACK  = "/feedback";
const RESET     = "/reset";

const messagesEl = document.getElementById("chat-messages");
const inputEl    = document.getElementById("chat-input");
const cityEl     = document.getElementById("city-select");

/* ── Navigation ─────────────────────────────────────────────────── */

function startChat() {
    document.getElementById("landing").classList.add("hidden");
    document.getElementById("chatbot").classList.remove("hidden");
    addBotBubble(
        "👋 Hello! I'm your AI health assistant.\n\n" +
        "Describe your symptoms in plain language and I'll analyze them using our " +
        "machine learning engine to identify possible conditions and recommend specialists.\n\n" +
        "**Tip:** Select your city above for local doctor recommendations.\n\n" +
        "**Example:** \"I have a headache, fever, and body ache for 3 days.\""
    );
    inputEl.focus();
}

function closeChat() {
    document.getElementById("chatbot").classList.add("hidden");
    document.getElementById("landing").classList.remove("hidden");
}

function resetChat() {
    messagesEl.innerHTML = "";
    fetch(RESET, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ session_id: SESSION_ID }),
    }).catch(() => {});
    addBotBubble(
        "🔄 Session reset. Describe your symptoms to start a new assessment."
    );
    inputEl.focus();
}

/* ── Send Message ───────────────────────────────────────────────── */

async function sendMessage() {
    const text = inputEl.value.trim();
    if (!text) return;

    addUserBubble(text);
    inputEl.value = "";
    inputEl.disabled = true;

    const typing = showTyping();

    try {
        const city = cityEl ? cityEl.value : "";
        const res = await fetch(WEBHOOK, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ session_id: SESSION_ID, message: text, city: city || undefined }),
        });

        if (res.status === 429) {
            removeEl(typing);
            addBotBubble("⏳ Too many requests. Please wait a moment and try again.");
            return;
        }

        const data = await res.json();
        removeEl(typing);
        renderResponse(data);
    } catch (err) {
        removeEl(typing);
        addBotBubble("⚠️ Something went wrong. Please check your connection and try again.");
        console.error(err);
    } finally {
        inputEl.disabled = false;
        inputEl.focus();
    }
}

/* Enter key */
inputEl.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
    }
});

/* ── Render Responses ───────────────────────────────────────────── */

function renderResponse(data) {
    switch (data.type) {
        case "emergency":   renderEmergency(data);   break;
        case "followup":    renderFollowup(data);    break;
        case "no_match":    renderNoMatch(data);      break;
        case "result":      renderResult(data);       break;
        case "error":       addBotBubble(data.message); break;
        default:            addBotBubble(data.message || "Sorry, I didn't understand that.");
    }
}

/* ── Emergency ──────────────────────────────────────────────────── */

function renderEmergency(data) {
    const card = document.createElement("div");
    card.className = "emergency-card";

    let numbersHtml = "";
    if (data.numbers) {
        numbersHtml = `
            <div class="emergency-numbers">
                <div class="en-title">Emergency Numbers (India)</div>
                <div class="en-item">📞 <strong>Emergency:</strong> ${esc(data.numbers.general || "112")}</div>
                <div class="en-item">🚑 <strong>Ambulance:</strong> ${esc(data.numbers.ambulance || "108")}</div>
                ${data.numbers.mental_health ? `<div class="en-item">💙 <strong>Mental Health:</strong> ${esc(data.numbers.mental_health)}</div>` : ""}
            </div>
        `;
    }

    card.innerHTML = `
        <div class="emer-title">🚨 ${esc(data.level || "EMERGENCY")} ALERT</div>
        <div class="emer-body">${md(data.message)}</div>
        ${numbersHtml}
        <div class="disclaimer">${md(data.disclaimer || "")}</div>
    `;
    messagesEl.appendChild(card);
    scrollBottom();
}

/* ── Follow-up ──────────────────────────────────────────────────── */

function renderFollowup(data) {
    addBotBubble(data.message);
}

/* ── No match ───────────────────────────────────────────────────── */

function renderNoMatch(data) {
    addBotBubble(data.message);
    if (data.disclaimer) addDisclaimer(data.disclaimer);
}

/* ── Full Result Card ───────────────────────────────────────────── */

function renderResult(data) {
    const card = document.createElement("div");
    card.className = "result-card";

    let html = `<h3>🏥 Health Assessment</h3>`;

    /* Conditions */
    html += `<div class="result-section"><div class="label">Possible Conditions</div>`;
    for (const c of data.conditions) {
        const level = getLevel(c.confidence);
        html += `
            <div class="condition-row">
                <span class="condition-name">${esc(c.disease)}</span>
                <div class="confidence-bar">
                    <div class="bar-track">
                        <div class="bar-fill ${level}" style="width:${c.confidence * 100}%"></div>
                    </div>
                    <span class="confidence-pct">${esc(c.confidence_pct)}</span>
                </div>
            </div>
            <span class="interpretation-badge ${level}">${esc(c.interpretation)}</span>`;

        /* Influencing symptoms */
        if (c.influencing_symptoms && c.influencing_symptoms.length > 0) {
            html += `<div class="symptom-tags">`;
            for (const s of c.influencing_symptoms) {
                html += `<span class="symptom-tag">${esc(s)}</span>`;
            }
            html += `</div>`;
        }
    }
    html += `</div>`;

    /* Explanation */
    html += `<div class="result-section">
        <div class="label">Based On</div>
        <div class="value">${md(data.explanation)}</div>
    </div>`;

    /* Triage */
    html += `<div class="result-section">
        <div class="label">Suggested Action</div>
        <div class="value">${md(data.triage)}</div>
    </div>`;

    /* Doctor Recommendation */
    if (data.doctor_recommendation) {
        const dr = data.doctor_recommendation;
        html += `<div class="result-section">
            <div class="label">Recommended Specialist — ${esc(dr.specialist)}</div>
            <div class="doctor-cards">`;

        for (const doc of dr.doctors) {
            const initials = doc.name.replace("Dr. ", "").split(" ").map(w => w[0]).join("").slice(0, 2);
            const stars = doc.rating ? "⭐".repeat(Math.round(doc.rating)) : "";
            const ratingText = doc.rating ? `${doc.rating}/5` : "";

            html += `
                <div class="doctor-card">
                    <div class="doctor-avatar">${initials}</div>
                    <div class="doctor-info">
                        <div class="doc-name">${esc(doc.name)}</div>
                        <div class="doc-hospital">${esc(doc.hospital)}</div>
                        <div class="doc-meta">
                            📍 ${esc(doc.city)}, ${esc(doc.state)}
                            ${doc.experience_years ? ` · ${doc.experience_years}y exp` : ""}
                            ${doc.consultation_fee ? ` · ${esc(doc.consultation_fee)}` : ""}
                            ${doc.available_days ? ` · ${esc(doc.available_days)}` : ""}
                        </div>
                        ${ratingText ? `<div class="doc-rating">${stars} ${ratingText}</div>` : ""}
                    </div>
                </div>`;
        }
        html += `</div></div>`;
    }

    /* Disclaimer */
    html += `<div class="disclaimer">${md(data.disclaimer)}</div>`;

    /* Feedback */
    const feedbackId = "fb-" + Date.now();
    html += `
        <div class="feedback-row" id="${feedbackId}">
            <span>Was this helpful?</span>
            <button class="btn-feedback" onclick="sendFeedback('up','${feedbackId}',this)" title="Helpful">👍</button>
            <button class="btn-feedback" onclick="sendFeedback('down','${feedbackId}',this)" title="Not helpful">👎</button>
        </div>`;

    card.innerHTML = html;
    messagesEl.appendChild(card);
    scrollBottom();

    /* Animate confidence bars */
    requestAnimationFrame(() => {
        card.querySelectorAll(".bar-fill").forEach(bar => {
            const w = bar.style.width;
            bar.style.width = "0%";
            requestAnimationFrame(() => { bar.style.width = w; });
        });
    });
}

/* ── Feedback ───────────────────────────────────────────────────── */

async function sendFeedback(vote, containerId, btn) {
    const row = document.getElementById(containerId);
    row.querySelectorAll(".btn-feedback").forEach(b => b.classList.remove("selected"));
    btn.classList.add("selected");
    try {
        await fetch(FEEDBACK, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ session_id: SESSION_ID, vote }),
        });
    } catch (_) { /* silent */ }
}

/* ── Bubble Helpers ─────────────────────────────────────────────── */

function addUserBubble(text) {
    const div = document.createElement("div");
    div.className = "bubble user";
    div.textContent = text;
    messagesEl.appendChild(div);
    scrollBottom();
}

function addBotBubble(text) {
    const div = document.createElement("div");
    div.className = "bubble bot";
    div.innerHTML = md(text);
    messagesEl.appendChild(div);
    scrollBottom();
}

function addDisclaimer(text) {
    const div = document.createElement("div");
    div.className = "bubble bot disclaimer";
    div.innerHTML = md(text);
    messagesEl.appendChild(div);
    scrollBottom();
}

/* ── Typing Indicator ───────────────────────────────────────────── */

function showTyping() {
    const div = document.createElement("div");
    div.className = "typing-indicator";
    div.innerHTML = `<span></span><span></span><span></span>`;
    messagesEl.appendChild(div);
    scrollBottom();
    return div;
}

function removeEl(el) {
    if (el && el.parentNode) el.parentNode.removeChild(el);
}

/* ── Utilities ──────────────────────────────────────────────────── */

function scrollBottom() {
    requestAnimationFrame(() => {
        messagesEl.scrollTop = messagesEl.scrollHeight;
    });
}

function esc(s) {
    if (s === undefined || s === null) return "";
    const d = document.createElement("div");
    d.textContent = String(s);
    return d.innerHTML;
}

/** Minimal markdown: **bold**, \n → <br> */
function md(text) {
    if (!text) return "";
    return esc(text)
        .replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>")
        .replace(/\n/g, "<br>");
}

function getLevel(confidence) {
    if (confidence > 0.7) return "high";
    if (confidence >= 0.4) return "medium";
    return "low";
}
