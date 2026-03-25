// ── State ───────────────────────────────────────────────────────
let ws_conn = null;
let threads = [];
let currentThread = null;
let currentMessages = [];
let targets = [];
let selectedRoute = 'any';
let routePinnedByUser = false;
let currentRun = null;
let runExpanded = false;
let runs = [];
let works = [];
let fwkList = [];
let lifecycleWorks = {blueprints: [], sawmill: [], factory: []};
let currentFwk = '';
let sectionState = {blueprints: false, sawmill: true, factory: false, scratchpad: false, brain: false};
let scratchpadThreads = [];
let brainThoughts = [];
let brainStats = {total: 0, tags: {}};
let currentWorks = null;
let currentContextFrameworkId = '';
let currentLifecycleSection = '';
let frameworks = [];
let currentManifest = null;
let selectedFrameworkId = '';
let manifestLoading = false;
let currentView = 'empty';
let runPanelStatus = '';
let runPanelStatusColor = 'var(--text-dim)';
let agents = [];
let selectedAgent = null;
let editingAgentName = null;
let providerModels = [];
let blueprintCardCollapsed = {};
let blueprintCardSeen = {};

const CLI_COLORS = {
  claude: '#a855f7', codex: '#22c55e', gemini: '#3b82f6',
  human: '#6366f1', system: '#6b7280',
};
const ACTIVE_HEARTBEAT_SECONDS = 600;
const CLAUDE_MODELS = ['claude-opus-4-6', 'claude-sonnet-4-6', 'claude-opus-4-5', 'claude-sonnet-4-5', 'claude-haiku-4-5'];
const CLAUDE_EFFORTS = ['low', 'medium', 'high', 'max', 'default'];
const CODEX_MODELS = ['gpt-5.4', 'gpt-5.4-mini', 'gpt-5.4-nano', 'o3', 'o3-mini', 'o4-mini', 'gpt-4.1', 'gpt-4.1-mini', 'gpt-4.1-nano', 'gpt-4o', 'gpt-4o-mini', 'default'];
const GEMINI_MODELS = ['gemini-3.1-pro-preview', 'gemini-3-flash-preview', 'gemini-2.5-pro', 'gemini-2.5-flash', 'gemini-2.5-flash-lite', 'gemini-2.0-flash', 'default'];
const PROVIDER_SECRET_ENV = {
  anthropic: 'ANTHROPIC_API_KEY',
  openai: 'OPENAI_API_KEY',
  google: 'GOOGLE_API_KEY',
};

function agentColor(agent, cli) {
  if (CLI_COLORS[cli]) return CLI_COLORS[cli];
  if (CLI_COLORS[agent]) return CLI_COLORS[agent];
  // Stable hash color for unknown agents
  let h = 0;
  for (let i = 0; i < agent.length; i++) h = agent.charCodeAt(i) + ((h << 5) - h);
  return `hsl(${Math.abs(h) % 360}, 60%, 55%)`;
}

function interactiveRouteConfig(agentName) {
  if (!agentName || agentName === 'any' || agentName === 'human') return null;
  const agent = agents.find(candidate => candidate.name === agentName);
  if (!agent || !agent.enabled) return null;
  if (agent.agent_type !== 'interactive') return null;
  if (!agent.provider || !agent.model) return null;
  return agent;
}

function providerNeedsApiKey(provider) {
  return ['anthropic', 'openai', 'google'].includes(provider);
}

function canonicalCredentialsRef(provider) {
  return PROVIDER_SECRET_ENV[provider] || '';
}

function looksLikeRawSecret(value) {
  const text = String(value || '').trim();
  return text.startsWith('sk-') || text.startsWith('sk-ant-') || text.startsWith('AIza');
}

function agentInitial(agent) {
  if (agent === 'human') return 'H';
  return (agent || '?')[0].toUpperCase();
}

function formatTime(iso) {
  if (!iso) return '';
  const d = new Date(iso + (iso.endsWith('Z') ? '' : 'Z'));
  const now = new Date();
  const diff = now - d;
  if (diff < 86400000 && d.getDate() === now.getDate()) {
    return d.toLocaleTimeString([], {hour: '2-digit', minute: '2-digit'});
  }
  return d.toLocaleDateString([], {month: 'short', day: 'numeric'}) + ' ' +
         d.toLocaleTimeString([], {hour: '2-digit', minute: '2-digit'});
}

function shortTime(iso) {
  if (!iso) return '';
  const d = new Date(iso + (iso.endsWith('Z') ? '' : 'Z'));
  const now = new Date();
  const diff = now - d;
  if (diff < 60000) return 'now';
  if (diff < 3600000) return Math.floor(diff/60000) + 'm';
  if (diff < 86400000) return Math.floor(diff/3600000) + 'h';
  return d.toLocaleDateString([], {month: 'short', day: 'numeric'});
}

function worksTags(frameworkId) {
  return frameworkId ? [frameworkId] : [];
}

function detailCardsForWorks(work) {
  const latestRun = work.latest_run || {};
  return [
    {
      title: 'Blueprint',
      value: work.blueprint.task_md_exists ? 'TASK.md ready' : 'TASK.md missing',
      sub: work.blueprint.source_material_exists ? 'SOURCE_MATERIAL present' : 'SOURCE_MATERIAL optional',
    },
    {
      title: 'Sawmill',
      value: latestRun.run_id || 'No runs',
      sub: `${latestRun.state || 'not started'}${latestRun.current_turn ? ` · ${latestRun.current_turn}` : ''}`,
    },
    {
      title: 'Factory',
      value: String(work.artifacts.exists ? work.artifacts.file_count : 0),
      sub: work.artifacts.exists ? 'staging artifacts present' : 'not started',
    },
  ];
}

function sidebarAgentPrefix(sectionKey) {
  return {
    blueprints: 'blueprint-',
    sawmill: 'sawmill-',
    factory: 'factory-',
  }[sectionKey] || '';
}

function sectionAgents(sectionKey) {
  const prefix = sidebarAgentPrefix(sectionKey);
  if (!prefix) return [];
  return agents.filter(agent => agent.enabled && agent.name.startsWith(prefix));
}

function generalSidebarAgents() {
  return agents.filter(agent =>
    agent.enabled &&
    !agent.name.startsWith('blueprint-') &&
    !agent.name.startsWith('sawmill-') &&
    !agent.name.startsWith('factory-')
  );
}

function relevantAgentsForSection(sectionKey) {
  const prefix = sidebarAgentPrefix(sectionKey);
  return prefix ? agents.filter(agent => agent.enabled && agent.name.startsWith(prefix)) : [];
}

function renderDetailCards(cards) {
  return cards.map(card => `
    <div class="works-summary-card">
      <div class="works-summary-label">${escHtml(card.title)}</div>
      <div class="works-summary-value">${escHtml(card.value)}</div>
      <div class="works-summary-sub">${escHtml(card.sub)}</div>
    </div>
  `).join('');
}

function contextualAgentsForWork(work) {
  const active = (work?.agents || []).filter(agent => agent && agent.enabled && agent.active_in_works);
  const scoped = relevantAgentsForSection(currentLifecycleSection);
  const byName = new Map();
  [...active, ...scoped].forEach(agent => {
    if (!byName.has(agent.name)) byName.set(agent.name, agent);
  });
  return Array.from(byName.values());
}

function routeToContextAgent(agentName) {
  selectedRoute = agentName;
  routePinnedByUser = true;
  syncRouteSelect();
  updateTalkingTo();
  const input = document.getElementById('msg-input');
  if (input) input.focus();
}

function openSectionAgent(agentName, sectionKey='') {
  selectedRoute = agentName;
  routePinnedByUser = true;
  currentLifecycleSection = sectionKey || currentLifecycleSection;
  syncRouteSelect();
  updateTalkingTo();
  selectAgent(agentName);
}

function renderSidebarAgentCard(agent, sectionKey='') {
  const isActive = selectedRoute === agent.name || (selectedAgent && selectedAgent.name === agent.name);
  return `
    <div class="sidebar-agent-card ${isActive ? 'active' : ''}" onclick="openSectionAgent('${escHtml(agent.name)}', '${escHtml(sectionKey)}')">
      <div class="sidebar-agent-name"><span class="agent-dot" style="background:${agentStatusColor(agent)}"></span>${escHtml(agent.name)}</div>
      <div class="sidebar-agent-meta">${escHtml(agent.provider || agent.cli || '')} · ${escHtml(agent.agent_type || 'interactive')}</div>
    </div>
  `;
}

function renderContextualAgents(work) {
  const availableAgents = contextualAgentsForWork(work);
  if (!availableAgents.length) {
    return `
      <div class="context-agent-empty">
        <span>No agents active.</span>
        <button class="btn-secondary" onclick="showAgentModal()">+ Agent</button>
      </div>
    `;
  }
  const defaultRoute = routePinnedByUser ? selectedRoute : computeDefaultRoute();
  return `
    <div class="context-agent-grid">
      ${availableAgents.map(agent => `
        <div class="context-agent-card">
          <div class="context-agent-top">
            <div class="context-agent-name">
              <span class="agent-dot" style="background:${agentStatusColor(agent)}"></span>
              ${escHtml(agent.name)}
            </div>
            ${defaultRoute === agent.name ? '<span class="context-agent-badge">Default</span>' : ''}
          </div>
          <div class="context-agent-sub">${escHtml(agent.provider || agent.cli || '')} · ${escHtml(agent.agent_type || 'interactive')}</div>
          <div class="context-agent-actions">
            <button class="btn-inline" onclick="routeToContextAgent('${escHtml(agent.name)}')">Talk</button>
            <button class="btn-inline" onclick="showAgentModal('${escHtml(agent.name)}')">Edit</button>
          </div>
        </div>
      `).join('')}
    </div>
  `;
}

// ── WebSocket ───────────────────────────────────────────────────
function connectWS() {
  const proto = location.protocol === 'https:' ? 'wss:' : 'ws:';
  ws_conn = new WebSocket(`${proto}//${location.host}/ws?token=`);

  ws_conn.onopen = () => {
    document.getElementById('conn-dot').className = 'conn-dot connected';
    document.getElementById('conn-text').textContent = 'Connected';
  };

  ws_conn.onclose = () => {
    document.getElementById('conn-dot').className = 'conn-dot disconnected';
    document.getElementById('conn-text').textContent = 'Disconnected';
    setTimeout(connectWS, 3000);
  };

  ws_conn.onerror = () => {
    document.getElementById('conn-dot').className = 'conn-dot disconnected';
    document.getElementById('conn-text').textContent = 'Error';
  };

  ws_conn.onmessage = (e) => {
    const data = JSON.parse(e.data);
    if (data.type === 'thread_list') {
      threads = data.threads;
      renderThreadList();
      fetchWorks();
      if (currentFwk) fetchFwkWorks(currentFwk).then(() => renderSidebar());
    } else if (data.type === 'thread_update') {
      if (currentThread === data.thread_id) {
        currentMessages = data.messages;
        renderMessages();
      }
      // Also refresh thread list
      fetchThreads();
      fetchWorks();
      if (currentFwk) fetchFwkWorks(currentFwk).then(() => renderSidebar());
    } else if (data.type === 'run_status') {
      currentRun = data.run || null;
      renderRunCard();
      fetchRuns();
    } else if (data.type === 'sent') {
      if (!currentThread && data.message && data.message.thread_id) {
        openThread(data.message.thread_id);
      }
    }
  };
}

// ── Data fetching ───────────────────────────────────────────────
async function fetchThreads() {
  try {
    const r = await fetch('/api/threads');
    threads = await r.json();
  } catch(e) {}
}

async function fetchWorks() {
  try {
    const r = await fetch('/api/works');
    const data = await r.json();
    works = data.works || [];
    scratchpadThreads = data.scratchpad || [];
    if (selectedFrameworkId && !works.some(work => work.framework_id === selectedFrameworkId)) {
      selectedFrameworkId = '';
      currentWorks = null;
    }
    if (!selectedFrameworkId && works.length) {
      selectedFrameworkId = works[0].framework_id;
    }
    renderThreadList();
  } catch (e) {
    works = [];
    scratchpadThreads = [];
    renderThreadList();
  }
}

async function fetchBrainStats() {
  try {
    const r = await fetch('/api/brain/stats');
    brainStats = r.ok ? await r.json() : {total: 0, tags: {}};
  } catch (e) {
    brainStats = {total: 0, tags: {}};
  }
}

async function fetchBrainThoughts(limit=20, tag='') {
  try {
    const params = new URLSearchParams({limit: String(limit)});
    if (tag) params.set('tag', tag);
    const r = await fetch(`/api/brain/thoughts?${params.toString()}`);
    brainThoughts = r.ok ? await r.json() : [];
  } catch (e) {
    brainThoughts = [];
  }
}

async function fetchFwkList() {
  try {
    const r = await fetch('/api/fwk');
    fwkList = await r.json();
    if (!currentFwk && fwkList.length) {
      currentFwk = fwkList[0].fwk_id;
    }
  } catch (e) {
    fwkList = [];
  }
}

async function fetchFwkWorks(fwkId) {
  try {
    const r = await fetch(`/api/fwk/${fwkId}/works`);
    lifecycleWorks = r.ok ? await r.json() : {blueprints: [], sawmill: [], factory: []};
  } catch (e) {
    lifecycleWorks = {blueprints: [], sawmill: [], factory: []};
  }
}

async function fetchWorksDetail(frameworkId) {
  if (!frameworkId) return null;
  try {
    const r = await fetch(`/api/works/${frameworkId}`);
    if (!r.ok) return null;
    currentWorks = await r.json();
    return currentWorks;
  } catch (e) {
    return null;
  }
}

async function fetchRuns() {
  try {
    const r = await fetch('/api/runs');
    runs = await r.json();
  } catch (e) {
    runs = [];
  }
}

async function fetchFrameworks() {
  try {
    const r = await fetch('/api/frameworks');
    frameworks = await r.json();
    if (selectedFrameworkId && !frameworks.some(f => f.framework_id === selectedFrameworkId)) {
      selectedFrameworkId = '';
    }
    if (!selectedFrameworkId && frameworks.length) {
      selectedFrameworkId = frameworks[0].framework_id;
    }
  } catch (e) {
    frameworks = [];
    selectedFrameworkId = '';
  }
}

async function fetchManifest(frameworkId) {
  manifestLoading = true;
  if (!frameworkId) {
    currentManifest = null;
    manifestLoading = false;
    return;
  }
  try {
    const r = await fetch(`/api/manifest/${frameworkId}`);
    currentManifest = r.ok ? await r.json() : null;
  } catch (e) {
    currentManifest = null;
  } finally {
    manifestLoading = false;
  }
}

async function fetchTargets() {
  try {
    const r = await fetch('/api/targets');
    targets = await r.json();
    populateTargets();
  } catch(e) {}
}

async function fetchAgents() {
  try {
    const r = await fetch('/api/agents');
    agents = await r.json();
    renderAgents();
    populateTargets();
    if (selectedAgent) {
      const next = agents.find(a => a.name === selectedAgent.name);
      if (next) {
        renderAgentDetail(next);
      } else if (!currentThread) {
        selectedAgent = null;
        document.getElementById('chat-header').style.display = 'none';
        document.getElementById('input-bar').style.display = 'none';
        document.getElementById('messages').innerHTML = '<div class="empty-state"><div><p>Select a conversation or start a new one</p><div class="hint">Messages appear in real-time via WebSocket</div></div></div>';
      }
    }
  } catch(e) {}
}

function populateTargets() {
  const sel = document.getElementById('route-select');
  const newTo = document.getElementById('new-to');
  [sel, newTo].forEach(s => {
    s.innerHTML = '';
    targets.forEach(t => {
      const opt = document.createElement('option');
      opt.value = t;
      opt.textContent = t;
      s.appendChild(opt);
    });
  });
  applyRouteState();
}

function updateTalkingTo() {
  const el = document.getElementById('talking-to');
  if (!el) return;
  const route = routePinnedByUser ? selectedRoute : computeDefaultRoute();
  const agent = agents.find(candidate => candidate.name === route);
  if (agent) {
    el.innerHTML = `Talking to <strong>${escHtml(agent.name)}</strong> · ${escHtml(agent.provider || agent.cli || 'agent')}`;
  } else if (route && route !== 'any') {
    el.innerHTML = `Talking to <strong>${escHtml(route)}</strong>`;
  } else {
    el.innerHTML = 'Talking to <strong>any</strong>';
  }
}

function toggleRoutePicker() {
  const wrap = document.getElementById('route-picker-wrap');
  if (!wrap) return;
  wrap.style.display = wrap.style.display === 'none' ? 'block' : 'none';
}

function formatAge(seconds) {
  if (seconds === null || seconds === undefined) return 'no heartbeat';
  if (seconds < 60) return `${seconds}s ago`;
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
  return `${Math.floor(seconds / 3600)}h ago`;
}

function runClass(run) {
  if (!run || !run.state) return 'complete';
  if (run.state === 'running' && (run.last_orchestrator_phase || run.last_worker_phase || '').includes('waiting')) return 'waiting';
  if (run.state === 'running') return 'running';
  if (run.state === 'failed' || run.state === 'escalated') return 'failed';
  return 'complete';
}

function renderRunCard() {
  const card = document.getElementById('run-card');
  if (!card) return;
  const title = document.getElementById('run-title');
  const meta = document.getElementById('run-meta');
  const events = document.getElementById('run-events');
  const run = currentRun;

  card.className = `run-card ${runClass(run)}`;
  if (!run || !run.run_id) {
    title.textContent = 'No active sawmill run';
    meta.textContent = 'No runs discovered';
    events.innerHTML = '';
    events.className = 'run-events';
    return;
  }

  title.textContent = `${run.framework} • ${run.state || 'unknown'}`;
  const phase = run.current_step || run.current_turn || 'idle';
  meta.innerHTML = `${phase} · ${run.current_role || 'no active role'}<br>${run.latest_event_summary || 'No recent events'}<br>Heartbeat ${formatAge(run.heartbeat_age_seconds)}`;
  const recent = (run.events || []).slice(-5).reverse();
  events.innerHTML = recent.map(ev => `<div class="run-detail">${escHtml((ev.timestamp || '').slice(11, 19))} · ${escHtml(ev.summary || ev.event_type || '')}</div>`).join('');
  events.className = runExpanded && recent.length ? 'run-events open' : 'run-events';
}

function renderTopStrip() {
  const strip = document.getElementById('top-strip');
  if (!strip) return;
  if (!currentContextFrameworkId && currentView !== 'works') {
    strip.style.display = 'none';
    strip.innerHTML = '';
    return;
  }

  const work = currentWorks && currentWorks.framework_id === currentContextFrameworkId
    ? currentWorks
    : null;
  const latestRun = work?.latest_run || {};
  const stripState = currentLifecycleSection === 'blueprints'
    ? (work?.blueprint?.blueprint_state || work?.state || 'not_started')
    : (work?.state || 'not_started');
  const activeAgents = (work?.agents || []).filter(agent => agent.active_in_works);
  const blueprintAgent = agents.find(agent => agent.name === 'blueprint-agent');
  const presenceAgents = [...activeAgents];
  if (currentLifecycleSection === 'blueprints' && blueprintAgent && !presenceAgents.some(agent => agent.name === blueprintAgent.name)) {
    presenceAgents.unshift({...blueprintAgent, active_in_works: false});
  }
  const selectedPresence = routePinnedByUser ? selectedRoute : computeDefaultRoute();
  const avatars = presenceAgents.slice(0, 5).map(agent => `
    <button class="presence-avatar ${agent.active_in_works ? 'active' : ''} ${selectedPresence === agent.name ? 'selected' : ''}" style="background:${agentColor(agent.name, agent.cli)}" title="${escHtml(agent.name)}" onclick="setRouteFromPresence('${escHtml(agent.name)}')">${escHtml(agentInitial(agent.name))}</button>
  `).join('');
  const eventText = latestRun.latest_event_summary || 'No recent event';
  const heartbeatText = latestRun.heartbeat_age_seconds === undefined ? 'idle' : `heartbeat ${formatAge(latestRun.heartbeat_age_seconds)}`;

  strip.style.display = '';
  strip.innerHTML = `
    <div class="top-strip-main">
      <div>
        <div class="top-strip-title">${escHtml(currentContextFrameworkId || work?.framework_id || 'Scratchpad')}</div>
        <div class="top-strip-sub">${escHtml(eventText)} · ${escHtml(heartbeatText)}</div>
      </div>
      <div class="top-strip-badge ${escHtml(stripState)}">${escHtml(stripState || 'scratchpad')}</div>
      <div class="presence-row">${avatars || '<span class="top-strip-sub">No active agents</span>'}</div>
    </div>
    <div class="top-strip-actions">
      ${currentContextFrameworkId ? '<button class="btn-inline" onclick="showRunsPanel()">Manifest / Run</button>' : ''}
      ${currentContextFrameworkId ? '<button class="btn-inline" onclick="showNewThread()">New Works Thread</button>' : '<button class="btn-inline" onclick="showNewThread()">New Scratchpad Thread</button>'}
    </div>
  `;
}

function setRouteFromPresence(agentName) {
  selectedRoute = agentName;
  routePinnedByUser = true;
  syncRouteSelect();
  updateTalkingTo();
}

function toggleRunDetails() {
  runExpanded = !runExpanded;
  renderRunCard();
}

function frameworkHasActiveRun(frameworkId) {
  return runs.some(run =>
    run.framework === frameworkId &&
    ['running', 'retrying'].includes(run.state) &&
    run.heartbeat_age_seconds !== null &&
    run.heartbeat_age_seconds <= ACTIVE_HEARTBEAT_SECONDS
  );
}

function selectedFrameworkRun() {
  return runs.find(run =>
    run.framework === selectedFrameworkId &&
    ['running', 'retrying'].includes(run.state) &&
    run.heartbeat_age_seconds !== null &&
    run.heartbeat_age_seconds <= ACTIVE_HEARTBEAT_SECONDS
  ) || null;
}

async function showRunsPanel() {
  currentView = 'runs';
  currentContextFrameworkId = selectedFrameworkId || '';
  selectedAgent = null;
  currentThread = null;
  currentManifest = null;
  manifestLoading = true;
  runPanelStatus = '';
  runPanelStatusColor = 'var(--text-dim)';
  renderThreadList();
  renderAgents();
  document.getElementById('chat-header').style.display = '';
  document.getElementById('chat-title').textContent = 'Sawmill Run Control';
  document.getElementById('chat-participants').textContent = 'Requested config only · launch goes through run.sh';
  document.getElementById('input-bar').style.display = 'none';
  await fetchWorksDetail(currentContextFrameworkId);
  renderTopStrip();
  document.getElementById('messages').innerHTML = '<div class="empty-state"><div>Loading run control…</div></div>';
  try {
    await fetchFrameworks();
    await fetchRuns();
    if (!selectedFrameworkId && frameworks.length) {
      selectedFrameworkId = frameworks[0].framework_id;
    }
    await fetchManifest(selectedFrameworkId);
    renderRunsPanel();
  } catch (e) {
    runPanelStatus = `Failed to load run control: ${String(e)}`;
    runPanelStatusColor = '#ef4444';
    manifestLoading = false;
    renderRunsPanel();
  }
}

function renderManifestRows() {
  if (manifestLoading) {
    return '<tr><td colspan="5" style="color:var(--text-dim)">Loading requested config…</td></tr>';
  }
  if (!currentManifest || !currentManifest.roles) {
    return '<tr><td colspan="5" style="color:var(--text-dim)">No manifest data</td></tr>';
  }
  return currentManifest.roles.map(role => {
    const disabled = frameworkHasActiveRun(selectedFrameworkId) ? 'disabled' : '';
    const backend = role.backend || 'default';
    const options = (role.allowed_backends || []).map(backend =>
      `<option value="${backend}" ${backend === role.backend ? 'selected' : ''}>${backend}</option>`
    ).join('');
    let backendModelValues = ['default'];
    let backendEffortValues = ['default'];
    if (backend === 'claude') {
      backendModelValues = CLAUDE_MODELS;
      backendEffortValues = CLAUDE_EFFORTS;
    } else if (backend === 'codex') {
      backendModelValues = CODEX_MODELS;
    } else if (backend === 'gemini') {
      backendModelValues = GEMINI_MODELS;
    } else if (backend === 'mock') {
      backendModelValues = ['default'];
    }
    const modelValues = Array.from(new Set([role.model || 'default', 'default', ...backendModelValues]));
    const effortValues = Array.from(new Set([role.effort || 'default', 'default', ...backendEffortValues]));
    const modelOptions = modelValues.map(model =>
      `<option value="${model}" ${model === role.model ? 'selected' : ''}>${model}</option>`
    ).join('');
    const effortOptions = effortValues.map(effort =>
      `<option value="${effort}" ${effort === role.effort ? 'selected' : ''}>${effort}</option>`
    ).join('');
    const note = role.env_override_active
      ? `${role.source} · env override active (${escHtml(role.env_override)})`
      : role.source;
    return `
      <tr>
        <td>${escHtml(role.name)}</td>
        <td><select data-role="${escHtml(role.name)}" data-field="backend" onchange="handleManifestFieldChange('${escHtml(role.name)}','backend',this.value)" ${disabled}>${options}</select></td>
        <td><select data-role="${escHtml(role.name)}" data-field="model" onchange="handleManifestFieldChange('${escHtml(role.name)}','model',this.value)" ${disabled}>${modelOptions}</select></td>
        <td><select data-role="${escHtml(role.name)}" data-field="effort" onchange="handleManifestFieldChange('${escHtml(role.name)}','effort',this.value)" ${disabled}>${effortOptions}</select></td>
        <td class="manifest-source">${note}</td>
      </tr>
    `;
  }).join('');
}

function renderRunsPanel() {
  const el = document.getElementById('messages');
  const activeRun = selectedFrameworkRun();
  const disabled = !!activeRun;
  const frameworkOptions = frameworks.map(framework =>
    `<option value="${framework.framework_id}" ${framework.framework_id === selectedFrameworkId ? 'selected' : ''}>${framework.framework_id}</option>`
  ).join('');
  const launchDisabled = disabled || !selectedFrameworkId ? 'disabled' : '';
  const saveDisabled = disabled || !selectedFrameworkId ? 'disabled' : '';
  const statusText = activeRun
    ? `Active run: ${activeRun.run_id} · ${activeRun.state}`
    : (manifestLoading ? 'Loading manifest…' : (currentManifest ? 'Manifest saved values are requested config only.' : 'Select a framework to configure.'));
  const panelNote = manifestLoading
    ? 'Loading requested config…'
    : (currentManifest ? escHtml(currentManifest.label || 'Requested config') : 'Requested config');
  const statusMessage = runPanelStatus || (disabled
    ? 'Run is active. Requested config is read-only until it finishes.'
    : 'Requested config only. Runtime may still differ via env override.');
  el.innerHTML = `
    <div class="run-panel">
      <h2>Sawmill Run Control</h2>
      <div class="run-panel-note">This UI configures and launches runs, but execution authority stays with <code>./sawmill/run.sh</code>.</div>
      <div class="run-form-row">
        <div>
          <label>Framework</label>
          <select id="framework-picker" onchange="changeFramework(this.value)">${frameworkOptions}</select>
        </div>
        <div>
          <label>Status</label>
          <input value="${escHtml(statusText)}" readonly>
        </div>
      </div>
      <div class="run-panel-note">${panelNote}</div>
      <table class="manifest-table">
        <thead>
          <tr>
            <th>Role</th>
            <th>Backend</th>
            <th>Model</th>
            <th>Effort</th>
            <th>Source</th>
          </tr>
        </thead>
        <tbody>${renderManifestRows()}</tbody>
      </table>
      <div class="agent-actions" style="margin-top:16px">
        <button class="btn-cancel" onclick="refreshManifest()">Reload</button>
        <button class="btn-new" onclick="saveManifest()" ${saveDisabled}>Save Manifest</button>
        <button class="btn-new" onclick="launchFrameworkRun()" ${launchDisabled}>Launch Run</button>
      </div>
      <div class="field-note" id="manifest-status" style="color:${runPanelStatusColor}">${statusMessage}</div>
    </div>
  `;
}

async function changeFramework(frameworkId) {
  selectedFrameworkId = frameworkId;
  currentView = 'runs';
  currentManifest = null;
  manifestLoading = true;
  runPanelStatus = '';
  runPanelStatusColor = 'var(--text-dim)';
  document.getElementById('messages').innerHTML = '<div class="empty-state"><div>Loading run control…</div></div>';
  await fetchRuns();
  await fetchManifest(frameworkId);
  renderRunsPanel();
}

function handleManifestFieldChange(roleName, field, value) {
  if (!currentManifest || !currentManifest.roles) return;
  const row = currentManifest.roles.find(role => role.name === roleName);
  if (!row) return;
  row[field] = value;
  if (field === 'backend') {
    if (value === 'claude') {
      row.model = CLAUDE_MODELS.includes(row.model) ? row.model : 'claude-sonnet-4-6';
      row.effort = CLAUDE_EFFORTS.includes(row.effort) ? row.effort : 'medium';
    } else if (value === 'codex') {
      row.model = CODEX_MODELS.includes(row.model) ? row.model : 'gpt-5.4';
      row.effort = 'default';
    } else if (value === 'gemini') {
      row.model = GEMINI_MODELS.includes(row.model) ? row.model : 'gemini-2.5-pro';
      row.effort = 'default';
    } else {
      row.model = 'default';
      row.effort = 'default';
    }
    renderRunsPanel();
  }
}

async function refreshManifest() {
  runPanelStatus = '';
  runPanelStatusColor = 'var(--text-dim)';
  document.getElementById('messages').innerHTML = '<div class="empty-state"><div>Loading run control…</div></div>';
  await fetchManifest(selectedFrameworkId);
  renderRunsPanel();
}

async function saveManifest() {
  const payload = {
    roles: Object.fromEntries((currentManifest?.roles || []).map(role => [role.name, {
      backend: role.backend,
      model: role.model,
      effort: role.effort,
    }])),
  };
  const r = await fetch(`/api/manifest/${selectedFrameworkId}`, {
    method: 'PUT',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify(payload),
  });
  const data = await r.json();
  if (!r.ok) {
    runPanelStatus = data.error || 'Failed to save manifest';
    runPanelStatusColor = '#ef4444';
    renderRunsPanel();
    return;
  }
  runPanelStatus = 'Manifest saved. Ready to launch.';
  runPanelStatusColor = '#22c55e';
  await fetchManifest(selectedFrameworkId);
  renderRunsPanel();
}

async function launchFrameworkRun() {
  const r = await fetch('/api/run/launch', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({framework: selectedFrameworkId}),
  });
  const data = await r.json();
  if (!r.ok) {
    runPanelStatus = data.error || 'Failed to launch run';
    runPanelStatusColor = '#ef4444';
    renderRunsPanel();
    return;
  }
  runPanelStatus = `Launched ${data.framework} (pid ${data.pid}). Live progress is shown in the run monitor card above.`;
  runPanelStatusColor = '#22c55e';
  await fetchRuns();
  renderRunsPanel();
}

function computeDefaultRoute() {
  const contextual = contextualDefaultRoute();
  if (contextual) return contextual;
  for (let i = currentMessages.length - 1; i >= 0; i--) {
    const agent = currentMessages[i].from_agent || currentMessages[i].from_cli || '';
    if (agent && agent !== 'human') return agent;
  }
  const thread = threads.find(t => t.thread_id === currentThread);
  if (thread) {
    const nonHuman = (thread.participants || []).filter(p => p !== 'human');
    if (nonHuman.length) return nonHuman[0];
  }
  return 'any';
}

function contextualDefaultRoute() {
  if (currentLifecycleSection === 'blueprints' && currentContextFrameworkId && targets.includes('blueprint-agent')) {
    return 'blueprint-agent';
  }
  return '';
}

function applyRouteState() {
  if (!routePinnedByUser) {
    selectedRoute = computeDefaultRoute();
  }
  syncRouteSelect();
  updateTalkingTo();
}

// ── Thread list rendering ───────────────────────────────────────
function renderThreadList() {
  renderSidebar();
}

function lifecycleSection(label, key, items, placeholder='') {
  const expanded = !!sectionState[key];
  const scopedAgents = sectionAgents(key);
  const body = expanded
    ? ((items.length
      ? items.map(item => renderWorksItem(item, key)).join('')
      : `<div class="lifecycle-placeholder">${escHtml(placeholder || 'No frameworks')}</div>`) +
      (scopedAgents.length ? `<div class="sidebar-agent-divider">agents</div>${scopedAgents.map(agent => renderSidebarAgentCard(agent, key)).join('')}` : ''))
    : '';
  return `
    <div class="lifecycle-section">
      <div class="lifecycle-header" onclick="toggleLifecycleSection('${key}')">${expanded ? '▾' : '▸'} ${label}</div>
      <div class="lifecycle-body" style="display:${expanded ? 'block' : 'none'}">${body}</div>
    </div>
  `;
}

function formatBrainDistance(distance) {
  if (distance === undefined || distance === null || Number.isNaN(Number(distance))) return '';
  return ` · d=${Number(distance).toFixed(3)}`;
}

function truncateBrainText(text, maxLength=96) {
  const value = String(text || '');
  if (value.length <= maxLength) return value;
  return `${value.slice(0, maxLength - 1)}…`;
}

async function captureBrainThought() {
  const input = document.getElementById('brain-capture-input');
  if (!input) return;
  const content = input.value.trim();
  if (!content) return;
  const r = await fetch('/api/brain/capture', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({
      content,
      tags: currentContextFrameworkId ? [currentContextFrameworkId] : [],
      source: 'shell-ui',
    }),
  });
  if (!r.ok) {
    alert('Failed to save thought');
    return;
  }
  input.value = '';
  await fetchBrainStats();
  await fetchBrainThoughts();
  renderSidebar();
}

async function searchBrain() {
  const input = document.getElementById('brain-search-input');
  if (!input) return;
  const query = input.value.trim();
  if (!query) {
    await fetchBrainThoughts();
    renderSidebar();
    return;
  }
  const r = await fetch('/api/brain/search', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({query, limit: 10}),
  });
  if (!r.ok) {
    alert('Brain search failed');
    return;
  }
  brainThoughts = await r.json();
  renderSidebar();
}

function renderBrainSection() {
  const expanded = !!sectionState.brain;
  const topTags = Object.entries(brainStats.tags || {})
    .sort((a, b) => b[1] - a[1])
    .slice(0, 3)
    .map(([tag, count]) => `${tag} ${count}`)
    .join(', ');
  const rows = brainThoughts.length
    ? brainThoughts.map(thought => `
        <div class="brain-thought">
          <div class="brain-thought-content">${escHtml(truncateBrainText(thought.content || ''))}</div>
          <div class="brain-thought-meta">${escHtml(thought.source || 'local')} · ${escHtml(shortTime(thought.created_at || ''))}${escHtml(formatBrainDistance(thought.distance))}</div>
        </div>
      `).join('')
    : '<div class="lifecycle-placeholder">No thoughts stored</div>';
  const body = expanded ? `
    <div class="brain-controls">
      <div class="brain-input-row">
        <input id="brain-search-input" class="brain-input" placeholder="Search memory by meaning">
        <button class="btn-inline" onclick="searchBrain()">Search</button>
      </div>
      <div class="brain-input-row">
        <input id="brain-capture-input" class="brain-input" placeholder="Capture a thought">
        <button class="btn-inline" onclick="captureBrainThought()">Save</button>
      </div>
      <div class="works-summary-sub">Thoughts: ${escHtml(String(brainStats.total || 0))}${topTags ? ` · top tags: ${escHtml(topTags)}` : ''}</div>
      <div class="brain-thought-list">${rows}</div>
    </div>
  ` : '';
  return `
    <div class="lifecycle-section">
      <div class="lifecycle-header" onclick="toggleLifecycleSection('brain')">${expanded ? '▾' : '▸'} Brain <span class="section-count">(${brainStats.total || 0})</span></div>
      <div class="lifecycle-body" style="display:${expanded ? 'block' : 'none'}">${body}</div>
    </div>
  `;
}

function renderSidebar() {
  const fwkSelect = document.getElementById('fwk-select');
  const fwkDescription = document.getElementById('fwk-description');
  const blueprintsEl = document.getElementById('blueprints-section');
  const sawmillEl = document.getElementById('sawmill-section');
  const factoryEl = document.getElementById('factory-section');
  const generalAgentsEl = document.getElementById('general-agents-section');
  const scratchpadEl = document.getElementById('scratchpad-section');
  const brainEl = document.getElementById('brain-section');
  if (!blueprintsEl || !sawmillEl || !factoryEl || !generalAgentsEl || !scratchpadEl || !brainEl) return;

  if (fwkSelect) {
    fwkSelect.innerHTML = fwkList.map(fwk =>
      `<option value="${escHtml(fwk.fwk_id)}" ${fwk.fwk_id === currentFwk ? 'selected' : ''}>${escHtml(fwk.fwk_id)} — ${escHtml(fwk.name)}</option>`
    ).join('');
  }
  if (fwkDescription) {
    const current = fwkList.find(fwk => fwk.fwk_id === currentFwk);
    fwkDescription.textContent = current ? current.description : '';
  }

  blueprintsEl.innerHTML = lifecycleSection('Blueprints', 'blueprints', lifecycleWorks.blueprints || [], 'No frameworks in blueprint stage.');
  sawmillEl.innerHTML = lifecycleSection('Sawmill', 'sawmill', lifecycleWorks.sawmill || [], 'No frameworks in sawmill stage.');
  factoryEl.innerHTML = lifecycleSection('Factory', 'factory', lifecycleWorks.factory || [], 'No frameworks promoted yet. KERNEL boot requires all 6 frameworks to pass.');
  const unmatchedAgents = generalSidebarAgents();
  generalAgentsEl.innerHTML = unmatchedAgents.length ? `
    <div class="lifecycle-section">
      <div class="lifecycle-header">Agents</div>
      <div class="lifecycle-body" style="display:block">${unmatchedAgents.map(agent => renderSidebarAgentCard(agent, '')).join('')}</div>
    </div>
  ` : '';

  const scratchBody = scratchpadThreads.length
    ? scratchpadThreads.map(t => renderThreadItem(t)).join('')
    : '<div class="lifecycle-placeholder">No scratchpad threads</div>';
  scratchpadEl.innerHTML = `
    <div class="lifecycle-section">
      <div class="lifecycle-header" onclick="toggleLifecycleSection('scratchpad')">${sectionState.scratchpad ? '▾' : '▸'} Scratchpad <span class="section-count">(${scratchpadThreads.length})</span></div>
      <div class="lifecycle-body" style="display:${sectionState.scratchpad ? 'block' : 'none'}">${scratchBody}</div>
    </div>
  `;
  brainEl.innerHTML = renderBrainSection();
}

function toggleLifecycleSection(key) {
  sectionState[key] = !sectionState[key];
  renderSidebar();
}

async function changeFwk(fwkId) {
  currentFwk = fwkId;
  await fetchFwkWorks(fwkId);
  renderSidebar();
}

function agentStatusColor(agent) {
  if (!agent.enabled) return '#6b7280';
  if (!agent.last_seen) return '#6b7280';
  const age = Date.now() - new Date(agent.last_seen + (agent.last_seen.endsWith('Z') ? '' : 'Z')).getTime();
  return age <= 300000 ? '#22c55e' : '#6b7280';
}

function providerIcon(provider) {
  return {
    'anthropic': '🟣',
    'codex-cli': '🟢',
    'google': '🔵',
    'ollama': '🟠',
    'openai': '⚪',
  }[provider] || '•';
}

function renderAgents() {
  const el = document.getElementById('agent-list');
  if (!el) return;
  if (!agents.length) {
    el.innerHTML = '<div style="padding:8px 4px;color:var(--text-muted);font-size:12px">No agents</div>';
    return;
  }
  el.innerHTML = agents.map(agent => `
    <div class="agent-item ${selectedAgent && selectedAgent.name === agent.name ? 'active' : ''}" onclick="selectAgent('${agent.name}')">
      <div class="agent-row">
        <div class="agent-name"><span class="agent-dot" style="background:${agentStatusColor(agent)}"></span>${providerIcon(agent.provider)} ${escHtml(agent.name)}</div>
        <span class="agent-badge">${escHtml(agent.agent_type || 'interactive')}</span>
      </div>
      <div class="agent-sub">${escHtml(agent.provider || agent.cli || '')}${agent.enabled ? '' : ' · disabled'}</div>
    </div>
  `).join('');
}

function selectAgent(name) {
  currentView = 'agent';
  const agent = agents.find(a => a.name === name);
  if (!agent) return;
  selectedAgent = agent;
  currentThread = null;
  renderThreadList();
  renderAgents();
  renderTopStrip();
  renderAgentDetail(agent);
  updateTalkingTo();
}

function renderAgentDetail(agent) {
  selectedAgent = agent;
  const el = document.getElementById('messages');
  document.getElementById('chat-header').style.display = '';
  document.getElementById('chat-title').textContent = agent.name;
  document.getElementById('chat-participants').textContent = `${agent.provider || agent.cli || 'agent'} · ${agent.agent_type}${agent.enabled ? '' : ' · disabled'}`;
  document.getElementById('input-bar').style.display = 'none';
  el.innerHTML = `
    <div class="agent-panel">
      <h2>${escHtml(agent.name)}</h2>
      <div class="agent-grid">
        <div class="label">Provider</div><div>${escHtml(agent.provider || '')}</div>
        <div class="label">Model</div><div>${escHtml(agent.model || '')}</div>
        <div class="label">Type</div><div>${escHtml(agent.agent_type || '')}</div>
        <div class="label">Enabled</div><div>${agent.enabled ? 'yes' : 'no'}</div>
        <div class="label">Task Types</div><div>${escHtml((agent.task_types || []).join(', '))}</div>
        <div class="label">Context</div><div>${escHtml(agent.context_mode || '')}</div>
        <div class="label">Timeout</div><div>${escHtml(String(agent.timeout || ''))}</div>
        <div class="label">Max Retries</div><div>${escHtml(String(agent.max_retries || ''))}</div>
        <div class="label">Last Seen</div><div>${escHtml(agent.last_seen || 'never')}</div>
        <div class="label">Instructions</div><div>${escHtml(agent.instructions || '')}</div>
      </div>
      <div class="agent-actions">
        <button class="btn-new" onclick="showAgentModal('${escHtml(agent.name)}')">Edit</button>
        <button class="btn-cancel" onclick="toggleAgentEnabled('${escHtml(agent.name)}', ${agent.enabled ? 'false' : 'true'})">${agent.enabled ? 'Disable' : 'Enable'}</button>
        <button class="btn-cancel" onclick="deleteAgent('${escHtml(agent.name)}')">Delete</button>
      </div>
    </div>
  `;
}

function renderThreadItem(t) {
  const isActive = currentThread === t.thread_id;
  const openFn = t.binding_source === 'scratchpad'
    ? `openScratchpadThread('${t.thread_id}')`
    : `openThread('${t.thread_id}')`;
  const dots = (t.participants || []).map(p => {
    const color = CLI_COLORS[p] || agentColor(p, '');
    return `<span class="participant-dot" style="background:${color}" title="${p}"></span>`;
  }).join('');

  return `
    <div class="thread-item ${isActive ? 'active' : ''}" onclick="${openFn}">
      <div class="thread-summary">
        ${t.has_active ? '<span class="active-badge"></span>' : ''}
        ${escHtml(t.summary || t.thread_id)}
      </div>
      <div class="thread-meta">
        <span class="thread-participants">${dots}</span>
        <span>${t.message_count} msg${t.message_count !== 1 ? 's' : ''}</span>
        <span>${shortTime(t.latest)}</span>
      </div>
    </div>
  `;
}

function openScratchpadThread(threadId) {
  currentContextFrameworkId = '';
  currentLifecycleSection = '';
  currentWorks = null;
  openThread(threadId);
}

function renderBlueprintDependencySummary(details) {
  if (!details || !details.length) return 'deps: none';
  const allPassed = details.every(dep => dep.passed);
  const suffix = details.map(dep => {
    const shortId = (dep.framework_id || '').replace('FMWK-', '').split('-')[0];
    return `${shortId} ${dep.passed ? '✓' : '✗'}`;
  }).join(', ');
  return `deps: ${allPassed ? '✓' : '✗'} (${suffix})`;
}

function renderWorksItem(work, sectionKey='') {
  const isActive = (currentView === 'works' || currentView === 'chat' || currentView === 'runs') && selectedFrameworkId === work.framework_id;
  const latestRun = work.latest_run || null;
  const effectiveState = work.awaiting_promotion ? 'awaiting_promotion' : (work.state || 'not_started');
  if (sectionKey === 'blueprints') {
    const blueprintState = work.blueprint.blueprint_state || 'not_started';
    const taskStatus = work.blueprint.task_md_exists ? '✓' : '✗';
    const sourceStatus = work.blueprint.source_material_exists ? '✓' : '✗';
    const depSummary = renderBlueprintDependencySummary(work.blueprint.dependency_details);
    return `
      <div class="works-card blueprint-card ${isActive ? 'active' : ''}" onclick="openWorks('${work.framework_id}', 'blueprints')">
        <div class="works-title-row">
          <div class="works-title"><span class="works-dot ${escHtml(blueprintState)}"></span>${escHtml(work.framework_id)}</div>
        </div>
        <div class="works-meta">
          ${escHtml(work.sidebar_summary || blueprintState.replace('_', ' '))}<br>
          TASK.md: ${taskStatus} &nbsp; SOURCE: ${sourceStatus}<br>
          ${escHtml(depSummary)}
        </div>
      </div>
    `;
  }
  const lineOne = work.sidebar_summary || (
    latestRun
      ? `${latestRun.current_turn || latestRun.current_step || 'idle'} · ${latestRun.current_role || 'no active role'}`
      : `${work.blueprint.complete_count}/${work.blueprint.total_count} specs complete`
  );
  const lineTwo = latestRun
    ? `${shortTime(latestRun.latest_event_timestamp || latestRun.started_at)}`
    : (work.blueprint.complete_count === 0 ? 'not started' : `${work.blueprint.complete_count}/${work.blueprint.total_count} specs`);

  return `
    <div class="works-card ${isActive ? 'active' : ''} ${work.awaiting_promotion ? 'awaiting-promotion' : ''}" onclick="openWorks('${work.framework_id}', '${sectionKey || work.lifecycle_section || ''}')">
      <div class="works-title-row">
        <div class="works-title"><span class="works-dot ${escHtml(effectiveState)}"></span>${escHtml(work.framework_id)}</div>
        <div class="works-state ${escHtml(effectiveState)} ${work.awaiting_promotion ? 'compact' : ''}">${escHtml(work.awaiting_promotion ? 'awaiting promo' : (work.state || 'not_started'))}</div>
      </div>
      <div class="works-meta">${escHtml(lineOne)}${lineTwo ? `<br>${escHtml(lineTwo)}` : ''}</div>
    </div>
  `;
}

function latestWorksThread(work) {
  const rows = [...(work?.threads || [])];
  rows.sort((a, b) => String(b.latest || '').localeCompare(String(a.latest || '')));
  return rows[0] || null;
}

function toggleBlueprintSummary(frameworkId) {
  blueprintCardCollapsed[frameworkId] = !blueprintCardCollapsed[frameworkId];
  if (currentWorks && currentWorks.framework_id === frameworkId) {
    renderBlueprintOverview(currentWorks);
  }
}

function renderBlueprintSummaryBar(work) {
  const blueprint = work.blueprint || {};
  const depPassed = (blueprint.dependency_details || []).every(dep => dep.passed);
  const summary = `${work.framework_id} · ${(blueprint.blueprint_state || 'not_started').replace('_', ' ')} · ${blueprint.complete_count || 0}/${blueprint.total_count || 0} specs · deps ${depPassed ? '✓' : '✗'}`;
  return `<button class="blueprint-summary-toggle" onclick="toggleBlueprintSummary('${escHtml(work.framework_id)}')">${escHtml(summary)}</button>`;
}

async function openWorks(frameworkId, lifecycleSection='') {
  currentView = 'works';
  selectedFrameworkId = frameworkId;
  currentContextFrameworkId = frameworkId;
  currentLifecycleSection = lifecycleSection || '';
  currentThread = null;
  selectedAgent = null;
  routePinnedByUser = false;
  renderThreadList();
  document.getElementById('chat-header').style.display = '';
  document.getElementById('chat-title').textContent = frameworkId;
  document.getElementById('chat-participants').textContent = 'Works overview';
  document.getElementById('input-bar').style.display = 'none';
  renderTopStrip();
  document.getElementById('messages').innerHTML = '<div class="empty-state"><div>Loading Works…</div></div>';
  try {
    await fetchWorksDetail(frameworkId);
    if (currentLifecycleSection === 'blueprints' && currentWorks) {
      const existing = latestWorksThread(currentWorks);
      if (existing) {
        openWorksThread(existing.thread_id, frameworkId);
        return;
      }
      if (!(frameworkId in blueprintCardSeen)) {
        blueprintCardSeen[frameworkId] = true;
        blueprintCardCollapsed[frameworkId] = false;
      } else if (!(frameworkId in blueprintCardCollapsed)) {
        blueprintCardCollapsed[frameworkId] = true;
      }
      document.getElementById('input-bar').style.display = '';
    }
    renderTopStrip();
    renderWorksOverview(currentWorks);
  } catch (e) {
    document.getElementById('messages').innerHTML = '<div class="empty-state"><div>Failed to load Works view</div></div>';
  }
}

function renderWorksOverview(work) {
  if (currentLifecycleSection === 'blueprints') {
    renderBlueprintOverview(work);
    return;
  }
  const latestRun = work.latest_run || {};
  const activeAgents = (work.agents || []).filter(agent => agent.active_in_works).length;
  const detailCards = renderDetailCards(detailCardsForWorks(work));
  const threadRows = (work.threads || []).map(thread => `
    <div class="thread-item" onclick="openWorksThread('${thread.thread_id}', '${work.framework_id}')">
      <div class="thread-summary">${escHtml(thread.summary || thread.thread_id)}</div>
      <div class="thread-meta">
        <span>${thread.message_count} msg${thread.message_count !== 1 ? 's' : ''}</span>
        <span>${shortTime(thread.latest)}</span>
        <span>${escHtml(thread.binding_source || '')}</span>
      </div>
    </div>
  `).join('');

  document.getElementById('chat-title').textContent = work.framework_id;
  document.getElementById('chat-participants').textContent = `${work.state} · ${work.blueprint.task_md_exists ? 'TASK.md ready' : 'TASK.md missing'}`;
  document.getElementById('messages').innerHTML = `
    <div class="works-panel">
      <h2>${escHtml(work.framework_id)}</h2>
      <div class="works-panel-subtitle">Works overview. The rail now treats this framework as the primary navigation object.</div>
      <div class="works-summary-grid">
        ${detailCards}
      </div>
      <div class="works-actions">
        <button class="btn-secondary" onclick="showRunsPanel()">Open Run Control</button>
        <button class="btn-secondary" onclick="showNewThread()">New Works Thread</button>
        <button class="btn-secondary" onclick="showAgentModal()">+ Agent</button>
      </div>
      <div class="works-summary-card" style="margin-bottom:16px">
        <div class="works-summary-label">Agents</div>
        ${renderContextualAgents(work)}
      </div>
      <div class="works-summary-card" style="margin-bottom:16px">
        <div class="works-summary-label">Telemetry</div>
        <div class="works-summary-sub">State: ${escHtml(work.state)} · ${activeAgents} active agents · ${work.threads.length} works threads${latestRun.latest_event_summary ? `<br>Latest event: ${escHtml(latestRun.latest_event_summary)}` : ''}</div>
      </div>
      <div class="works-summary-label">Works Threads</div>
      <div class="works-thread-list">
        ${threadRows || '<div class="works-empty">No Works-scoped threads yet. Scratchpad remains available in the rail.</div>'}
      </div>
    </div>
  `;
}

function renderChecklistRow(label, passed, detail='') {
  return `
    <div class="readiness-row">
      <span class="readiness-label">${escHtml(label)}</span>
      <span class="readiness-value ${passed ? 'ok' : 'missing'}">${passed ? '✓' : '✗'}</span>
      ${detail ? `<span class="readiness-detail">${escHtml(detail)}</span>` : ''}
    </div>
  `;
}

function renderBlueprintOverview(work) {
  const blueprint = work.blueprint || {};
  const dependencies = blueprint.dependency_details || [];
  const dependencyRows = dependencies.length
    ? dependencies.map(dep => renderChecklistRow(dep.framework_id, !!dep.passed, dep.passed ? 'passed' : 'not passed')).join('')
    : '<div class="readiness-row"><span class="readiness-label">Dependencies</span><span class="readiness-value ok">✓</span><span class="readiness-detail">none</span></div>';
  const sawmillReady = blueprint.task_md_exists && blueprint.dependencies_met;
  const collapsed = !!blueprintCardCollapsed[work.framework_id];
  const greetingRoute = contextualDefaultRoute();
  const greetingAgent = agents.find(agent => agent.name === greetingRoute);

  document.getElementById('chat-title').textContent = work.framework_id;
  document.getElementById('chat-participants').textContent = `Blueprints · ${blueprint.blueprint_state || 'not_started'}`;
  document.getElementById('input-bar').style.display = '';
  document.getElementById('messages').innerHTML = `
    <div class="works-panel">
      <h2>${escHtml(work.framework_id)}</h2>
      <div class="works-panel-subtitle">${escHtml(work.owns || 'No ownership summary available.')}</div>
      <div class="compact-cards">
        <div class="works-summary-card compact ${collapsed ? 'collapsed' : ''}">
          <div class="works-summary-label">Readiness Checklist</div>
          ${collapsed ? renderBlueprintSummaryBar(work) : `<div class="readiness-list">
            ${renderChecklistRow('Sawmill prerequisite · TASK.md', !!blueprint.task_md_exists, blueprint.task_md_exists ? 'required input present' : 'required to start sawmill')}
            ${renderChecklistRow('Optional enrichment · SOURCE_MATERIAL.md', !!blueprint.source_material_exists, blueprint.source_material_exists ? 'extra design input available' : 'optional')}
            ${dependencyRows}
            ${renderChecklistRow('Sawmill ready', !!sawmillReady, sawmillReady ? 'ready to start' : (!blueprint.dependencies_met ? 'dependencies incomplete' : 'needs TASK.md'))}
          </div>`}
          <button class="btn-inline collapse-toggle" onclick="toggleBlueprintSummary('${escHtml(work.framework_id)}')">${collapsed ? 'Expand' : 'Collapse'}</button>
        </div>
        <div class="works-summary-card compact ${collapsed ? 'collapsed' : ''}">
          <div class="works-summary-label">Blueprint State</div>
          ${collapsed ? renderBlueprintSummaryBar(work) : `<div class="works-summary-sub">
            State: ${escHtml((blueprint.blueprint_state || 'not_started').replace('_', ' '))}<br>
            ${escHtml(sawmillReady ? 'Ready for sawmill' : (blueprint.dependencies_met ? 'Waiting on TASK.md' : 'Blocked by dependencies'))}
          </div>`}
          <button class="btn-inline collapse-toggle" onclick="toggleBlueprintSummary('${escHtml(work.framework_id)}')">${collapsed ? 'Expand' : 'Collapse'}</button>
        </div>
      </div>
      <div class="works-summary-card" style="margin-bottom:16px">
        <div class="works-summary-label">Agents</div>
        ${renderContextualAgents(work)}
      </div>
      <div class="greeting-card">
        ${greetingAgent
          ? `<div class="msg-group">
              <div class="msg-avatar" style="background:${agentColor(greetingAgent.name, greetingAgent.cli)}">${escHtml(agentInitial(greetingAgent.name))}</div>
              <div class="msg-body">
                <div class="msg-header">
                  <span class="msg-author" style="color:${agentColor(greetingAgent.name, greetingAgent.cli)}">${escHtml(greetingAgent.name)}</span>
                  <span class="msg-time">ready</span>
                </div>
                <div class="msg-content">${escHtml(`${greetingAgent.name} · Ready to help with ${work.framework_id}. Ask me about readiness, scope, dependencies, or what TASK.md should contain.`)}</div>
              </div>
            </div>`
          : '<div class="works-empty">No interactive agent is available for this framework yet.</div>'}
      </div>
    </div>
  `;
  if (blueprintCardSeen[work.framework_id] && blueprintCardCollapsed[work.framework_id] === false) {
    blueprintCardCollapsed[work.framework_id] = true;
  }
  applyRouteState();
}

function openWorksThread(threadId, frameworkId) {
  currentContextFrameworkId = frameworkId || '';
  selectedFrameworkId = frameworkId || selectedFrameworkId;
  openThread(threadId);
}

// ── Open thread ─────────────────────────────────────────────────
async function openThread(tid) {
  currentView = 'chat';
  // Unsubscribe old
  if (currentThread && ws_conn && ws_conn.readyState === 1) {
    ws_conn.send(JSON.stringify({action: 'unsubscribe', thread_id: currentThread}));
  }

  currentThread = tid;
  routePinnedByUser = false;
  renderThreadList();

  // Subscribe via WebSocket
  if (ws_conn && ws_conn.readyState === 1) {
    ws_conn.send(JSON.stringify({action: 'subscribe', thread_id: tid}));
  }

  // Also fetch via REST as backup
  try {
    const r = await fetch(`/api/thread/${tid}`);
    currentMessages = await r.json();
    renderMessages();
  } catch(e) {}

  // Show input bar
  document.getElementById('input-bar').style.display = '';
  document.getElementById('chat-header').style.display = '';

  // Update header
  const thread = threads.find(t => t.thread_id === tid);
  if (thread) {
    document.getElementById('chat-title').textContent = thread.summary || tid;
    document.getElementById('chat-participants').textContent = (thread.participants || []).join(', ');
  }
  if (!currentContextFrameworkId && currentMessages.length) {
    currentContextFrameworkId = currentMessages.find(m => m.framework_id)?.framework_id || '';
  }
  if (currentContextFrameworkId && (!currentWorks || currentWorks.framework_id !== currentContextFrameworkId)) {
    await fetchWorksDetail(currentContextFrameworkId);
  }
  renderTopStrip();
  applyRouteState();
}

// ── Message rendering ───────────────────────────────────────────
function renderMessages() {
  const el = document.getElementById('messages');
  if (!currentMessages.length) {
    el.innerHTML = '<div class="empty-state"><div>No messages in this thread</div></div>';
    return;
  }

  let html = '';
  if (currentContextFrameworkId && currentWorks && currentWorks.framework_id === currentContextFrameworkId) {
    const latestRun = currentWorks.latest_run || {};
    html += `
      <div class="works-context">
        <div class="works-context-grid">
          <div class="works-context-section">
            <div class="works-context-label">Blueprint</div>
            <div class="works-summary-sub">${escHtml(currentWorks.blueprint.task_md_exists ? 'TASK.md ready' : 'TASK.md missing')}</div>
          </div>
          <div class="works-context-section">
            <div class="works-context-label">Sawmill</div>
            <div class="works-summary-sub">${escHtml(latestRun.run_id || 'No run')} · ${escHtml(latestRun.state || currentWorks.state)}</div>
          </div>
          <div class="works-context-section">
            <div class="works-context-label">Factory</div>
            <div class="works-summary-sub">${escHtml(currentWorks.artifacts.exists ? `${currentWorks.artifacts.file_count} artifacts` : 'Not started')}</div>
          </div>
        </div>
        <div class="works-context-agents">
          <div class="works-context-label">Agents</div>
          ${renderContextualAgents(currentWorks)}
        </div>
      </div>
    `;
  }

  currentMessages.forEach(m => {
    const agent = m.from_agent || m.from_cli || '?';
    const cli = m.from_cli || '';
    const color = agentColor(agent, cli);
    const initial = agentInitial(agent);
    const time = formatTime(m.created_at);
    const status = m.status || '';
    const content = m.content || m.summary || '';

    html += `
      <div class="msg-group">
        <div class="msg-avatar" style="background:${color}">${initial}</div>
        <div class="msg-body">
          <div class="msg-header">
            <span class="msg-author" style="color:${color}">${escHtml(agent)}</span>
            <span class="msg-time">${time}</span>
            ${status ? `<span class="msg-status ${status}">${status}</span>` : ''}
          </div>
          <div class="msg-content">${escHtml(content)}</div>
          <div class="msg-type">${m.type || ''}${m.to ? ' → ' + escHtml(m.to) : ''}${m.framework_id ? ' · ' + escHtml(m.framework_id) : ''}</div>
        </div>
      </div>
    `;
  });

  el.innerHTML = html;
  el.scrollTop = el.scrollHeight;
  applyRouteState();
}

function handleRouteChange(value) {
  selectedRoute = value || 'any';
  routePinnedByUser = true;
  syncRouteSelect();
  updateTalkingTo();
  const wrap = document.getElementById('route-picker-wrap');
  if (wrap) wrap.style.display = 'none';
}

function syncRouteSelect() {
  const sel = document.getElementById('route-select');
  if (!sel) return;
  if (sel.querySelector(`option[value="${selectedRoute}"]`)) {
    sel.value = selectedRoute;
    return;
  }
  if (sel.querySelector('option[value="any"]')) {
    selectedRoute = 'any';
    sel.value = 'any';
    return;
  }
  if (sel.options.length) {
    selectedRoute = sel.options[0].value;
    sel.value = selectedRoute;
  }
}

async function sendMessage() {
  const input = document.getElementById('msg-input');
  const content = input.value.trim();
  if (!content) return;

  const effectiveRoute = routePinnedByUser ? selectedRoute : computeDefaultRoute();
  const to = effectiveRoute && effectiveRoute !== 'any' ? effectiveRoute : '';
  const interactiveConfig = interactiveRouteConfig(to);
  const type = document.getElementById('type-select').value;
  const lastMsg = currentMessages[currentMessages.length - 1];
  const replyTo = lastMsg ? lastMsg.id : '';
  const payload = {
    content: content,
    to: to,
    type: type,
    reply_to: replyTo,
    summary: content.substring(0, 80),
    tags: worksTags(currentContextFrameworkId),
    framework_id: currentContextFrameworkId || '',
    lifecycle_section: currentLifecycleSection || '',
    thread_id: currentThread || '',
  };

  if (interactiveConfig) {
    if (!ws_conn || ws_conn.readyState !== 1) {
      alert('Interactive agent requires a live WebSocket connection.');
      return;
    }
    ws_conn.send(JSON.stringify({
      action: 'interactive',
      ...payload,
    }));
    input.value = '';
    autoResize(input);
    return;
  }

  if (!currentThread) {
    const r = await fetch('/api/send', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify(payload),
    });
    const item = await r.json();
    input.value = '';
    autoResize(input);
    await fetchThreads();
    await fetchWorks();
    if (currentFwk) {
      await fetchFwkWorks(currentFwk);
      renderSidebar();
    }
    await openThread(item.thread_id || item.id);
    return;
  }

  // Send via WebSocket if connected
  if (ws_conn && ws_conn.readyState === 1) {
    ws_conn.send(JSON.stringify({
      action: 'send',
      ...payload,
    }));
  } else {
    // Fallback to REST
    await fetch('/api/send', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify(payload),
    });
  }

  input.value = '';
  autoResize(input);
}

// ── New thread ──────────────────────────────────────────────────
function showNewThread() {
  document.getElementById('new-thread-modal').style.display = '';
  document.getElementById('new-content').focus();
}

function toggleAgentProviderFields() {
  const provider = document.getElementById('agent-provider').value;
  const credentialsInput = document.getElementById('agent-credentials-ref');
  const credentialsNote = document.getElementById('agent-credentials-note');
  document.getElementById('agent-api-base-wrap').style.display = provider === 'ollama' ? '' : 'none';
  document.getElementById('agent-credentials-wrap').style.display = provider === 'ollama' || provider === 'codex-cli' ? 'none' : '';
  document.getElementById('agent-api-key-wrap').style.display = providerNeedsApiKey(provider) ? '' : 'none';
  if (providerNeedsApiKey(provider)) {
    credentialsInput.value = canonicalCredentialsRef(provider);
    credentialsInput.disabled = true;
    credentialsNote.textContent = 'Fixed for this provider. Paste the real secret below in API Key.';
  } else {
    credentialsInput.disabled = false;
    credentialsNote.textContent = provider === 'ollama' || provider === 'codex-cli'
      ? ''
      : 'Name of the environment variable to read at runtime.';
  }
}

function toggleAgentTypeFields() {
  const agentType = document.getElementById('agent-agent-type').value;
  const interactive = agentType === 'interactive';
  document.getElementById('agent-task-types-wrap').style.display = interactive ? 'none' : '';
  document.getElementById('agent-context-mode-wrap').style.display = interactive ? 'none' : '';
}

async function fetchProviderModels() {
  const provider = document.getElementById('agent-provider').value;
  const apiBase = encodeURIComponent(document.getElementById('agent-api-base').value.trim());
  const credentialsRef = encodeURIComponent(document.getElementById('agent-credentials-ref').value.trim());
  try {
    const r = await fetch(`/api/providers/${provider}/models?api_base=${apiBase}&credentials_ref=${credentialsRef}`);
    const data = await r.json();
    providerModels = Array.isArray(data) ? data : [];
  } catch (e) {
    providerModels = [];
  }
  const dl = document.getElementById('agent-model-options');
  dl.innerHTML = providerModels.map(model => `<option value="${escHtml(model.id || '')}"></option>`).join('');
  document.getElementById('agent-model-note').textContent = providerModels.length
    ? `Loaded ${providerModels.length} models`
    : 'No models discovered — enter model ID manually';
}

function handleProviderChange() {
  toggleAgentProviderFields();
  fetchProviderModels();
}

function handleAgentTypeChange() {
  toggleAgentTypeFields();
}

function showAgentModal(name='') {
  editingAgentName = name || null;
  document.getElementById('agent-error').textContent = '';
  const modal = document.getElementById('agent-modal');
  modal.style.display = '';
  const agent = name ? agents.find(a => a.name === name) : null;
  document.getElementById('agent-modal-title').textContent = agent ? `Edit Agent` : 'Create Agent';
  document.getElementById('agent-name').value = agent ? agent.name : '';
  document.getElementById('agent-name').disabled = !!agent;
  document.getElementById('agent-provider').value = agent ? (agent.provider || 'codex-cli') : 'codex-cli';
  document.getElementById('agent-model').value = agent ? (agent.model || '') : '';
  document.getElementById('agent-api-base').value = agent ? (agent.api_base || '') : '';
  document.getElementById('agent-credentials-ref').value = agent ? (agent.credentials_ref || '') : '';
  document.getElementById('agent-api-key').value = '';
  document.getElementById('agent-api-key-status').textContent = agent && agent.has_secret ? 'Key saved ✓' : 'No key set';
  document.getElementById('agent-api-key-status').style.color = agent && agent.has_secret ? '#22c55e' : 'var(--text-dim)';
  document.getElementById('agent-instructions').value = agent ? (agent.instructions || '') : '';
  document.getElementById('agent-task-types').value = agent ? (agent.task_types || []).join(',') : 'prompt,question';
  document.getElementById('agent-context-mode').value = agent ? (agent.context_mode || 'full_thread') : 'full_thread';
  document.getElementById('agent-timeout').value = agent ? (agent.timeout || 180) : 180;
  document.getElementById('agent-max-retries').value = agent ? (agent.max_retries || 2) : 2;
  document.getElementById('agent-agent-type').value = agent ? (agent.agent_type || 'worker') : 'worker';
  document.getElementById('agent-save-btn').textContent = agent ? 'Update' : 'Create';
  handleProviderChange();
  handleAgentTypeChange();
}

function hideAgentModal() {
  document.getElementById('agent-modal').style.display = 'none';
  editingAgentName = null;
  document.getElementById('agent-error').textContent = '';
}

async function saveAgent() {
  const provider = document.getElementById('agent-provider').value;
  const credentialsRef = providerNeedsApiKey(provider)
    ? canonicalCredentialsRef(provider)
    : document.getElementById('agent-credentials-ref').value.trim();
  if (looksLikeRawSecret(credentialsRef)) {
    document.getElementById('agent-error').textContent = 'This looks like a raw API key. Paste it into API Key, not API Key Env.';
    return;
  }
  const payload = {
    name: document.getElementById('agent-name').value.trim(),
    provider,
    model: document.getElementById('agent-model').value.trim(),
    api_base: document.getElementById('agent-api-base').value.trim(),
    credentials_ref: credentialsRef,
    instructions: document.getElementById('agent-instructions').value.trim(),
    task_types: document.getElementById('agent-agent-type').value === 'interactive'
      ? []
      : document.getElementById('agent-task-types').value.split(',').map(s => s.trim()).filter(Boolean),
    context_mode: document.getElementById('agent-agent-type').value === 'interactive'
      ? 'full_thread'
      : document.getElementById('agent-context-mode').value,
    timeout: parseInt(document.getElementById('agent-timeout').value || '180', 10),
    max_retries: parseInt(document.getElementById('agent-max-retries').value || '2', 10),
    agent_type: document.getElementById('agent-agent-type').value,
  };
  const method = editingAgentName ? 'PUT' : 'POST';
  const url = editingAgentName ? `/api/agents/${editingAgentName}` : '/api/agents';
  const r = await fetch(url, {
    method,
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify(payload),
  });
  const data = await r.json();
  if (!r.ok) {
    document.getElementById('agent-error').textContent = data.error || 'Failed to save agent';
    return;
  }
  const apiKey = document.getElementById('agent-api-key').value.trim();
  if (apiKey) {
    const secretResponse = await fetch(`/api/agents/${data.name}/secret`, {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({api_key: apiKey}),
    });
    const secretData = await secretResponse.json();
    if (!secretResponse.ok) {
      document.getElementById('agent-error').textContent = secretData.error || 'Failed to save API key';
      return;
    }
  }
  hideAgentModal();
  await fetchAgents();
  const createdOrUpdated = agents.find(a => a.name === data.name);
  if (createdOrUpdated) {
    renderAgentDetail(createdOrUpdated);
    renderAgents();
  }
}

async function testAgentConnection() {
  document.getElementById('agent-error').textContent = '';
  const apiKey = document.getElementById('agent-api-key').value.trim();
  const agentName = editingAgentName || document.getElementById('agent-name').value.trim();
  const provider = document.getElementById('agent-provider').value;
  const credentialsRef = providerNeedsApiKey(provider)
    ? canonicalCredentialsRef(provider)
    : document.getElementById('agent-credentials-ref').value.trim();
  if (looksLikeRawSecret(credentialsRef)) {
    document.getElementById('agent-error').style.color = '#ef4444';
    document.getElementById('agent-error').textContent = 'This looks like a raw API key. Paste it into API Key, not API Key Env.';
    return;
  }
  if (apiKey && agentName) {
    const secretResponse = await fetch(`/api/agents/${agentName}/secret`, {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({api_key: apiKey}),
    });
    const secretData = await secretResponse.json();
    if (!secretResponse.ok) {
      document.getElementById('agent-error').style.color = '#ef4444';
      document.getElementById('agent-error').textContent = secretData.error || 'Failed to save API key';
      return;
    }
    document.getElementById('agent-api-key').value = '';
    document.getElementById('agent-api-key-status').textContent = 'Key saved ✓';
    document.getElementById('agent-api-key-status').style.color = '#22c55e';
  }
  const payload = {
    name: editingAgentName || document.getElementById('agent-name').value.trim(),
    provider,
    model: document.getElementById('agent-model').value.trim(),
    api_base: document.getElementById('agent-api-base').value.trim(),
    credentials_ref: credentialsRef,
    instructions: document.getElementById('agent-instructions').value.trim(),
  };
  const r = await fetch('/api/agents/test', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify(payload),
  });
  const data = await r.json();
  let message = data.error || 'Connection failed';
  const match = /^Missing env var:\s*(.+)$/.exec(message);
  if (match && !providerNeedsApiKey(provider)) {
    message = `${match[1]} is not set in the shell environment`;
  } else if (match && providerNeedsApiKey(provider)) {
    message = 'No API key set. Paste a key into API Key and test again.';
  }
  document.getElementById('agent-error').style.color = r.ok ? '#22c55e' : '#ef4444';
  document.getElementById('agent-error').textContent = r.ok ? `Connection ok${data.context_window ? ` · context ${data.context_window}` : ''}` : message;
}

async function toggleAgentEnabled(name, enabled) {
  const r = await fetch(`/api/agents/${name}`, {
    method: 'PUT',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({enabled}),
  });
  if (r.ok) {
    await fetchAgents();
  }
}

async function deleteAgent(name) {
  if (!confirm(`Delete agent ${name}?`)) return;
  const r = await fetch(`/api/agents/${name}`, {method: 'DELETE'});
  if (r.ok) {
    if (selectedAgent && selectedAgent.name === name) {
      selectedAgent = null;
      document.getElementById('chat-header').style.display = 'none';
      document.getElementById('input-bar').style.display = 'none';
      document.getElementById('messages').innerHTML = '<div class="empty-state"><div><p>Select a conversation or start a new one</p><div class="hint">Messages appear in real-time via WebSocket</div></div></div>';
    }
    await fetchAgents();
  }
}

function hideNewThread() {
  document.getElementById('new-thread-modal').style.display = 'none';
  document.getElementById('new-content').value = '';
}

async function createThread() {
  const to = document.getElementById('new-to').value;
  const type = document.getElementById('new-type').value;
  const content = document.getElementById('new-content').value.trim();

  if (!content) {
    alert('Content is required');
    return;
  }

  try {
    const r = await fetch('/api/send', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({
        to,
        type,
        summary: content.substring(0, 80),
        content,
        tags: worksTags(currentContextFrameworkId),
        framework_id: currentContextFrameworkId || '',
        lifecycle_section: currentLifecycleSection || '',
      }),
    });
    const item = await r.json();
    hideNewThread();
    await fetchThreads();
    await fetchWorks();
    openThread(item.thread_id || item.id);
  } catch(e) {
    alert('Failed to create conversation');
  }
}

// ── Utilities ───────────────────────────────────────────────────
function escHtml(s) {
  const d = document.createElement('div');
  d.textContent = s || '';
  return d.innerHTML;
}

function autoResize(el) {
  el.style.height = 'auto';
  el.style.height = Math.min(el.scrollHeight, 160) + 'px';
}

window.addEventListener('error', (event) => {
  const text = document.getElementById('conn-text');
  const dot = document.getElementById('conn-dot');
  if (text) text.textContent = `UI error: ${event.message}`;
  if (dot) dot.className = 'conn-dot disconnected';
});

// ── Keyboard shortcuts ──────────────────────────────────────────
document.getElementById('msg-input').addEventListener('keydown', (e) => {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    sendMessage();
  }
});

document.getElementById('msg-input').addEventListener('input', function() {
  autoResize(this);
});

// ── Init ────────────────────────────────────────────────────────
fetchTargets();
fetchAgents();
fetchThreads();
fetchWorks();
fetchFwkList().then(() => fetchFwkWorks(currentFwk)).then(() => renderSidebar());
fetchFrameworks();
fetchRuns();
fetchBrainStats();
fetchBrainThoughts();
connectWS();
