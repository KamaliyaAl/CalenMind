"""
Vocab — All user-facing strings for the CalenMind AI bot.

## Traceability
Feature: F001 — Google OAuth Authentication, F002 — Multimodal Input Processing,
         F004 — Freemium Limits
Scenarios: SC001, SC002, SC003, SC004

## Business context
Centralises copy so UX changes don't require hunting through handler files.
Supports simple i18n extension in the future.
"""


class Vocab:
    # ── F001 Auth ─────────────────────────────────────────────────────────────
    AUTH_WELCOME = (
        "👋 Welcome to <b>CalenMind AI</b>!\n\n"
        "To get started, connect your Google Calendar."
    )
    AUTH_CONNECT_BUTTON = "🔗 Connect Google Calendar"
    AUTH_SUCCESS = "✅ Google Calendar connected successfully! Send me a photo, voice note, or text to create events."
    AUTH_ALREADY_CONNECTED = "✅ Your Google Calendar is already connected. What would you like to do?"
    AUTH_KEEP_BUTTON = "✅ Stay on this account"
    AUTH_SWITCH_BUTTON = "🔄 Switch Google Account"
    AUTH_KEEP_ACCOUNT = (
        "🎉 <b>Great! You're all set!</b>\n\n"
        "Just write me your plans and I'll add them to your Google Calendar. For example:\n"
        "• <i>Meeting with Anna tomorrow at 3 PM</i>\n"
        "• <i>Gym every Monday and Wednesday at 7 AM</i>\n"
        "• <i>Doctor appointment on Friday at 11:00</i>\n\n"
        "You can also send a <b>photo</b> of a schedule or a <b>voice note</b> 📸🎙️"
    )
    AUTH_EXIT_BUTTON = "🚪 Exit"
    AUTH_SWITCH_ACCOUNT_BUTTON = "🔄 Switch account"
    AUTH_NOT_CONNECTED = (
        "⚠️ Your Google Calendar is not connected yet.\n"
        "Use /start to connect."
    )

    # ── F002 Input Processing ─────────────────────────────────────────────────
    PROCESSING_PHOTO = "📸 Processing your photo… This may take up to a minute for complex schedules."
    PROCESSING_VOICE = "🎙️ Transcribing your voice note… Please wait."
    PROCESSING_TEXT = "✍️ Parsing your message…"
    EVENTS_CREATED = "📅 <b>{count} event(s)</b> added to your Google Calendar!\n\n{event_list}"
    EVENT_LINE = "• <b>{title}</b> — {start_time}"
    PARSING_ERROR = "❌ I couldn't extract any events from that. Please try again with a clearer input."

    # ── F004 Freemium ─────────────────────────────────────────────────────────
    FREEMIUM_LIMIT = (
        "🚫 You've used all <b>{limit} free syncs</b> for this month.\n\n"
        "Upgrade to <b>CalenMind Pro</b> for unlimited syncs. 🚀"
    )
    FREEMIUM_REMAINING = "📊 You have <b>{remaining}</b> free syncs left this month."

    # ── Generic ───────────────────────────────────────────────────────────────
    UNEXPECTED_ERROR = "❌ An unexpected error occurred. Please try again later."
    COMMAND_UNKNOWN = "I don't understand that command. Use /help to see available options."

    # ── Help ─────────────────────────────────────────────────────────────────
    HELP_TEXT = (
        "<b>CalenMind AI — Commands</b>\n\n"
        "/start — Connect Google Calendar\n"
        "/status — Check connection &amp; sync usage\n"
        "/switch — Connect a different Google account\n"
        "/exit — Disconnect Google Calendar\n"
        "/help — Show this message\n\n"
        "📸 Send a <b>photo</b> of a schedule\n"
        "🎙️ Send a <b>voice note</b> describing an event\n"
        "✍️ Send a <b>text message</b> with event details"
    )
