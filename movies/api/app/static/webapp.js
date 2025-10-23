(() => {
  const wsUrl = (location.protocol === 'https:' ? 'wss://' : 'ws://') + location.host + '/ws';
  const ws = new WebSocket(wsUrl);

  // Helpers
  const labels = [];
  const ctrData = [];
  const usersData = [];
  const engData = [];
  const precisionData = [];
  let topLabels = [];
  let topValues = [];

  const timeLabel = (ev) => {
    const end = new Date(ev.window_end || Date.now());
    return end.toLocaleTimeString();
  };

  const ctx1 = document.getElementById('ctrChart').getContext('2d');
  const ctrChart = new Chart(ctx1, {
    type: 'line',
    data: {
      labels,
      datasets: [
        { label: 'CTR (acceptance_rate)', data: ctrData, borderColor: '#38bdf8', backgroundColor: 'rgba(56,189,248,0.2)', tension: 0.25 },
        { label: 'Precision (proxy)', data: precisionData, borderColor: '#22c55e', backgroundColor: 'rgba(34,197,94,0.15)', tension: 0.25 }
      ]
    },
    options: { responsive: true, plugins: { legend: { labels: { color: '#cbd5e1' } } }, scales: { x: { ticks: { color: '#8aa0c8' } }, y: { min: 0, max: 1, ticks: { color: '#8aa0c8' } } } }
  });

  const ctx2 = document.getElementById('usersChart').getContext('2d');
  const usersChart = new Chart(ctx2, {
    type: 'line',
    data: { labels, datasets: [{ label: 'Usuarios activos/min', data: usersData, borderColor: '#a78bfa', backgroundColor: 'rgba(167,139,250,0.2)', tension: 0.25 }] },
    options: { responsive: true, plugins: { legend: { labels: { color: '#cbd5e1' } } }, scales: { x: { ticks: { color: '#8aa0c8' } }, y: { ticks: { color: '#8aa0c8' } } } }
  });

  const ctx3 = document.getElementById('engChart').getContext('2d');
  const engChart = new Chart(ctx3, {
    type: 'line',
    data: { labels, datasets: [{ label: 'Eventos prom./usuario', data: engData, borderColor: '#f59e0b', backgroundColor: 'rgba(245,158,11,0.2)', tension: 0.25 }] },
    options: { responsive: true, plugins: { legend: { labels: { color: '#cbd5e1' } } }, scales: { x: { ticks: { color: '#8aa0c8' } }, y: { ticks: { color: '#8aa0c8' } } } }
  });

  const ctx4 = document.getElementById('topChart').getContext('2d');
  const topChart = new Chart(ctx4, {
    type: 'bar',
    data: { labels: topLabels, datasets: [{ label: 'Sugerencias', data: topValues, backgroundColor: '#60a5fa' }] },
    options: { responsive: true, plugins: { legend: { labels: { color: '#cbd5e1' } } }, scales: { x: { ticks: { color: '#8aa0c8' } }, y: { ticks: { color: '#8aa0c8' } } } }
  });

  function pushLabel(lab) {
    if (labels.length > 50) {
      labels.shift(); ctrData.shift(); usersData.shift(); engData.shift(); precisionData.shift();
    }
    labels.push(lab);
  }

  function render() {
    ctrChart.update(); usersChart.update(); engChart.update(); topChart.update();
  }

  ws.onmessage = (ev) => {
    try {
      const msg = JSON.parse(typeof ev.data === 'string' ? ev.data : new TextDecoder().decode(ev.data));
      if (!msg.metric) return;
      switch (msg.metric) {
        case 'acceptance_rate': {
          const lab = timeLabel(msg);
          pushLabel(lab);
          ctrData.push(Number(msg.acceptance_rate || 0));
          break;
        }
        case 'precision': {
          const lab = timeLabel(msg);
          if (labels[labels.length - 1] !== lab) pushLabel(lab);
          precisionData.push(Number(msg.precision || 0));
          break;
        }
        case 'active_users': {
          const lab = timeLabel(msg);
          if (labels[labels.length - 1] !== lab) pushLabel(lab);
          usersData.push(Number(msg.active_users || 0));
          break;
        }
        case 'engagement': {
          const lab = timeLabel(msg);
          if (labels[labels.length - 1] !== lab) pushLabel(lab);
          engData.push(Number(msg.avg_events_per_user || 0));
          break;
        }
        case 'top_products': {
          const top = (msg.top || []).slice(0, 10);
          topLabels.length = 0; topValues.length = 0;
          for (const it of top) { topLabels.push(it.item_id); topValues.push(it.suggested); }
          break;
        }
      }
      render();
    } catch (e) {
      console.error('WS parse error', e);
    }
  };

  ws.onopen = () => console.log('WS conectado');
  ws.onclose = () => console.warn('WS desconectado');
})();
