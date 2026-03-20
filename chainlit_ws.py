"""
Chainlit Workspace — conversation UI backed by workspace.py.

Reads and writes through the same workspace.py API that portal.py and mcp_portal.py use.
No duplication. Chainlit is the conversation surface, workspace.py is the data layer.

Usage:
    chainlit run chainlit_ws.py
"""

import asyncio
import chainlit as cl
import workspace as ws


# ── Agent identity rendering ──────────────────────────────────────────────────

AGENT_AVATARS = {
    "claude": "🟣",
    "codex": "🟢",
    "gemini": "🔵",
    "human": "👤",
}


def get_agent_display(agent_name):
    """Get display name and avatar for an agent."""
    agents = ws.list_agents()
    for a in agents:
        if a["name"] == agent_name:
            cli = a.get("cli", "")
            return agent_name, AGENT_AVATARS.get(cli, "🤖")
    if agent_name == "human":
        return "Ray", "👤"
    return agent_name, "🤖"


# ── Thread rendering ─────────────────────────────────────────────────────────

async def render_thread(thread_id):
    """Render all turns in a workspace thread as Chainlit messages."""
    thread = ws.get_thread(thread_id)
    for item in thread:
        agent = item.get("from_agent", item.get("from_cli", "?"))
        content = item.get("content", "")
        summary = item.get("summary", "")
        display_name, avatar = get_agent_display(agent)

        msg = cl.Message(
            content=content or summary,
            author=display_name,
        )
        await msg.send()


# ── Startup ───────────────────────────────────────────────────────────────────

@cl.on_chat_start
async def on_start():
    """Show active threads and let user pick one or start new."""
    threads = ws.list_threads()
    active = [t for t in threads if any(
        it.get("status") in ("sent", "read") for it in t["items"])]

    if active:
        # Build thread picker
        actions = []
        for t in active[:10]:
            tid = t["thread_id"]
            summary = t["summary"][:50]
            participants = ", ".join(t["participants"][:3])
            actions.append(cl.Action(
                name="open_thread",
                payload={"thread_id": tid},
                label=f"{summary} ({participants})",
            ))
        actions.append(cl.Action(
            name="new_conversation",
            payload={},
            label="➕ New Conversation",
        ))

        await cl.Message(
            content=f"**{len(active)} active conversations.** Pick one or start new:",
            actions=actions,
        ).send()
    else:
        await cl.Message(
            content="No active conversations. Type a message to start one.",
        ).send()
        cl.user_session.set("mode", "new")


# ── Action handlers ───────────────────────────────────────────────────────────

@cl.action_callback("open_thread")
async def open_thread(action):
    thread_id = action.payload.get("thread_id", "")
    cl.user_session.set("thread_id", thread_id)
    cl.user_session.set("mode", "thread")

    # Render the thread
    thread = ws.get_thread(thread_id)
    if thread:
        last_item = thread[-1]
        cl.user_session.set("last_item_id", last_item.get("id", ""))
        # Get participants for default routing
        participants = set()
        for it in thread:
            agent = it.get("from_agent", it.get("from_cli", ""))
            if agent and agent != "human":
                participants.add(agent)
        cl.user_session.set("participants", list(participants))

    await render_thread(thread_id)
    await cl.Message(content="---\n_Thread loaded. Type to reply._").send()


@cl.action_callback("new_conversation")
async def new_conversation(action):
    cl.user_session.set("mode", "new_picking_route")

    # Show agent picker
    agents = ws.list_agents()
    targets = ws.get_routable_targets()
    actions = [
        cl.Action(name="set_route", payload={"to": t}, label=t)
        for t in targets if t != "any"
    ]
    await cl.Message(
        content="Who should receive this conversation?",
        actions=actions,
    ).send()


@cl.action_callback("set_route")
async def set_route(action):
    to = action.payload.get("to", "any")
    cl.user_session.set("route_to", to)
    cl.user_session.set("mode", "new")
    await cl.Message(content=f"Routing to **{to}**. Type your message.").send()


# ── Message handler ───────────────────────────────────────────────────────────

@cl.on_message
async def on_message(message: cl.Message):
    mode = cl.user_session.get("mode", "new")

    if mode == "thread":
        # Reply in existing thread
        thread_id = cl.user_session.get("thread_id", "")
        last_item_id = cl.user_session.get("last_item_id", "")
        participants = cl.user_session.get("participants", [])
        to = ",".join(participants) if participants else "any"

        item = ws.create_item(
            item_type="prompt",
            from_cli="human",
            from_agent="human",
            to=to,
            summary=message.content[:80],
            content=message.content,
            reply_to=last_item_id,
        )
        cl.user_session.set("last_item_id", item.get("id", ""))

        await cl.Message(
            content=f"_Sent to {to}_",
            author="system",
        ).send()

        # Fetch any new responses that arrived since last render
        await render_new_messages(thread_id)

    elif mode == "new":
        # Start new conversation
        route_to = cl.user_session.get("route_to", "any")

        item = ws.create_item(
            item_type="prompt",
            from_cli="human",
            from_agent="human",
            to=route_to,
            summary=message.content[:80],
            content=message.content,
        )
        thread_id = item.get("thread_id", item.get("id", ""))
        cl.user_session.set("thread_id", thread_id)
        cl.user_session.set("last_item_id", item.get("id", ""))
        cl.user_session.set("mode", "thread")
        cl.user_session.set("participants", [route_to])

        await cl.Message(
            content=f"_New conversation started. Sent to {route_to}_",
            author="system",
        ).send()

        # Fetch any new responses that arrived since last render
        await render_new_messages(thread_id)

    elif mode == "new_picking_route":
        # User typed before picking a route — use "any"
        cl.user_session.set("route_to", "any")
        cl.user_session.set("mode", "new")
        await on_message(message)  # re-process


# ── Response polling ──────────────────────────────────────────────────────────

async def render_new_messages(thread_id):
    """Fetch and render any new messages in the thread since last render."""
    seen = cl.user_session.get("seen_ids", set())
    thread = ws.get_thread(thread_id)

    for it in thread:
        iid = it.get("id", "")
        if iid in seen:
            continue
        seen.add(iid)

        agent = it.get("from_agent", it.get("from_cli", "?"))
        if agent == "human":
            continue

        content = it.get("content", "")
        summary = it.get("summary", "")
        display_name, avatar = get_agent_display(agent)

        await cl.Message(
            content=content or summary,
            author=display_name,
        ).send()

        cl.user_session.set("last_item_id", iid)

    cl.user_session.set("seen_ids", seen)


# ── Chat resume (thread persistence) ─────────────────────────────────────────

@cl.on_chat_resume
async def on_resume(thread):
    """Resume a previously opened thread."""
    thread_id = cl.user_session.get("thread_id", "")
    if thread_id:
        await render_thread(thread_id)
