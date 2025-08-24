Chart.defaults.color = 'white';

const API_URL = 'http://10.1.10.144:5000/api';
let data = [];

// Temporary Data
// const data = [
//   { timestamp: '4.04.2025, 4:00 PM', date: '3.04', floor: 1, plant: 'Mongoose', stage: 'seed planting', height: 0, leafColor: '-', humidity: 92, temperature: 26.0, notes: 'text text text' },
//   { timestamp: '5.04.2025, 4:00 PM', date: '4.04', floor: 1, plant: 'Basil', stage: 'sprouting', height: 2, leafColor: 'light green', humidity: 93, temperature: 25.5, notes: 'Leafs visible' },
//   { timestamp: '6.04.2025, 4:00 PM', date: '5.04', floor: 2, plant: 'Arugula', stage: 'leaf development', height: 5, leafColor: 'green', humidity: 90, temperature: 25.7, notes: 'Good growth' },
//   { timestamp: '7.04.2025, 4:00 PM', date: '6.04', floor: 1, plant: 'Tarragon', stage: 'flowering', height: 3, leafColor: 'yellow', humidity: 89, temperature: 25.8, notes: 'Flowering starts' },
//   { timestamp: '8.04.2025, 4:00 PM', date: '7.04', floor: 2, plant: 'Arugula', stage: 'leaf development', height: 4, leafColor: 'orange', humidity: 91, temperature: 25.6, notes: 'Leaf color changing' },
//   { timestamp: '9.04.2025, 4:00 PM', date: '8.04', floor: 1, plant: 'Beetroot Bordeaux', stage: 'end of cycle', height: 6, leafColor: 'dark green', humidity: 88, temperature: 25.4, notes: 'Harvest ready' },
//
//   // Duplicate entries for testing
//   ...new Array(5).fill().map((_, i) => ({
//     timestamp: `10.04.2025, 4:00 PM`,
//     date: '9.04',
//     floor: 1,
//     plant: 'Mongoose',
//     stage: 'seed planting',
//     height: 0,
//     leafColor: '-',
//     humidity: 92,
//     temperature: 26.0,
//     notes: `text ${i}`
//   }))
// ];


const rowsPerPage = 8;
let currentPage = 1;


function formatLocalDate(iso) {
  if (!iso) return '';
  const d  = new Date(iso);
  const yy = d.getFullYear();
  const mm = String(d.getMonth()+1).padStart(2, '0');
  const dd = String(d.getDate()).padStart(2, '0');
  return `${yy}-${mm}-${dd}`;
}


async function fetchData() {
  try {
    const res = await fetch(`${API_URL}/plants`);
    if (!res.ok) throw new Error(`Ошибка ${res.status}`);
    const raw = await res.json();
    console.log('raw response[0]:', raw[0]);  // см. реальные ключи в консоли
    // маппим в поля, которые ждёт таблица
    data = raw.map(item => ({
      timestamp:   formatDateTime(item.recorded_date),
      date:        formatLocalDate(item.seeding_date),
      floor:       item.floor       || '',
      plant:       item.name        || '',
      stage:       item.growth_days != null ? item.growth_days : '',
      height:      item.height      != null ? item.height : '',
      leafColor:   item.leaf_color  || '',
      humidity:    item.humidity    || '',
      temperature: item.temperature || '',
      notes:       item.description || '',
    }));
  } catch (err) {
    console.error(err);
    data = [];
  }
}

// simple helpers
function formatDateTime(iso) {
  if (!iso) return '';
  const d = new Date(iso);
  return d.toLocaleString();
}

// 2) рендер таблицы
function renderTable(filtered = data) {
  const tbody = document.querySelector('#dataTable tbody');
  tbody.innerHTML = '';
  const start = (currentPage - 1) * rowsPerPage;
  const pageData = filtered.slice(start, start + rowsPerPage);
  pageData.forEach(item => {
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td>${item.timestamp}</td>
      <td>${item.date}</td>
      <td>${item.floor}</td>
      <td>${item.plant}</td>
      <td>${item.stage}</td>
      <td>${item.height}</td>
      <td>${item.leafColor}</td>
      <td>${item.humidity}</td>
      <td>${item.temperature}</td>
      <td>${item.notes}</td>
    `;
    tbody.appendChild(tr);
  });
}
function renderPagination(filtered = data) {
  const pagination = document.getElementById('pagination');
  pagination.innerHTML = '';
  const pageCount = Math.ceil(filtered.length / rowsPerPage);
  for (let i = 1; i <= pageCount; i++) {
    const btn = document.createElement('button');
    btn.textContent = i;
    if (i === currentPage) btn.classList.add('active');
    btn.onclick = () => {
      currentPage = i;
      renderTable(filtered);
      renderPagination(filtered);
    };
    pagination.appendChild(btn);
  }
}

// Sorting Table Columns
let currentSortKey = null;
let currentSortAsc = true;

document.querySelectorAll('th').forEach(th => {
  th.addEventListener('click', () => {
    const key = th.getAttribute('data-key');
    const type = th.getAttribute('data-type');

    if (key === currentSortKey) {
      currentSortAsc = !currentSortAsc;
    } else {
      currentSortKey = key;
      currentSortAsc = true;
    }

    data.sort((a, b) => {
      const valA = a[key];
      const valB = b[key];
      if (type === 'number') return currentSortAsc ? valA - valB : valB - valA;
      return currentSortAsc
        ? String(valA).localeCompare(String(valB))
        : String(valB).localeCompare(String(valA));
    });

    updateSortIcons(key);
    currentPage = 1;
    renderTable();
    renderPagination();
  });
});

function updateSortIcons(activeKey) {
  document.querySelectorAll('th').forEach(th => {
    const key = th.getAttribute('data-key');
    th.innerHTML = th.textContent.split(' ')[0]; // Reset label
    if (key === activeKey) {
      th.innerHTML += currentSortAsc ? ' <span class="sort-arrow">▼</span>' : ' <span class="sort-arrow">▲</span>';
    }
  });
}


// Search Functionality
function filterData(query) {
  const lowerQuery = query.toLowerCase();
  return data.filter(entry =>
    Object.values(entry).some(val =>
      String(val).toLowerCase().includes(lowerQuery)
    )
  );
}

document.getElementById('searchBtn').addEventListener('click', () => {
  const query = document.getElementById('searchInput').value;
  const filtered = filterData(query);
  currentPage = 1;
  renderTable(filtered);
  renderPagination(filtered);
});

document.getElementById('searchInput').addEventListener('keypress', e => {
  if (e.key === 'Enter') {
    document.getElementById('searchBtn').click();
  }
});


// Tab Switching (Table/Analytics)
document.getElementById('tableBtn').onclick = () => {
  document.getElementById('tableSection').style.display = 'block';
  document.getElementById('analyticsSection').style.display = 'none';
  document.getElementById('tableBtn').classList.add('active');
  document.getElementById('analyticsBtn').classList.remove('active');
  document.getElementById('searchContainer').style.display = 'flex';
  document.getElementById('analyticsFilters').style.display = 'none';
};

document.getElementById('analyticsBtn').onclick = () => {
  document.getElementById('tableSection').style.display = 'none';
  document.getElementById('analyticsSection').style.display = 'block';
  document.getElementById('analyticsBtn').classList.add('active');
  document.getElementById('tableBtn').classList.remove('active');
  document.getElementById('searchContainer').style.display = 'none';
  document.getElementById('analyticsFilters').style.display = 'flex';
};


// Chart Initialization
let plantVarietyChart, temperatureChart, humidityChart, leafColorChart, growthStageChart, heightOverTimeChart;

function updateChart(chart, labels, data, label, type = 'bar') {
  chart.data.labels = labels;
  chart.data.datasets[0].label = label;
  chart.data.datasets[0].data = data;
  chart.update();
}


function createCharts() {
  const chartColor = '#287E8F';

  plantVarietyChart = new Chart(document.getElementById('plantVarietyChart'), {
    type: 'bar',
    data: { labels: [], datasets: [{ label: '', data: [], backgroundColor: [] }] },
    options: { responsive: true, plugins: { legend: { display: false } } }
  });

  temperatureChart = new Chart(document.getElementById('temperatureChart'), {
    type: 'line',
    data: { labels: [], datasets: [{ label: 'Temperature (°C)', data: [], borderColor: chartColor, tension: 0.3 }] },
    options: { responsive: true, plugins: { legend: { display: true } } }
  });

  humidityChart = new Chart(document.getElementById('humidityChart'), {
    type: 'line',
    data: { labels: [], datasets: [{ label: 'Humidity (%)', data: [], borderColor: chartColor, tension: 0.3 }] },
    options: { responsive: true, plugins: { legend: { display: true } } }
  });

  leafColorChart = new Chart(document.getElementById('leafColorChart'), {
    type: 'pie',
    data: {
      labels: [],
      datasets: [{ label: 'Leaf Colors', data: [], backgroundColor: [] }]
    },
    options: {
      responsive: true,
      plugins: {
        legend: {
          display: true,
          labels: {
            boxWidth: 20,
            padding: 10,
            maxWidth: 100
          },
          align: 'center',
          position: 'top'
        }
      }
    }
  });


  growthStageChart = new Chart(document.getElementById('growthStageChart'), {
    type: 'bar',
    data: { labels: [], datasets: [{ label: 'Growth Stages', data: [], backgroundColor: chartColor }] },
    options: { responsive: true }
  });

  heightOverTimeChart = new Chart(document.getElementById('heightOverTimeChart'), {
    type: 'line',
    data: { labels: [], datasets: [{ label: 'Height Over Time', data: [], borderColor: chartColor, tension: 0.3 }] },
    options: { responsive: true }
  });

}


// Update leaf Color Map
const leafColorMap = {
  'light green': '#9FFF8C',
  'green': '#42B66E',
  'dark green': '#17693B',
  'yellow': '#FBFF63',
  'orange': '#F4A03E',
  '-': '#B0B0B0' // grey for no color
};

function updateChart(chart, labels, data, label, type = 'bar') {
  chart.data.labels = labels;
  chart.data.datasets[0].label = label;
  chart.data.datasets[0].data = data;

  if (type === 'pie') {
    chart.data.datasets[0].backgroundColor = labels.map(l => leafColorMap[l] || '#CCCCCC');
  }

  chart.update();
}

// Update plant Color Map
const plantColorMap = {
  'Basil': '#9EFFC2',           // Light minty green
  'Tarragon': '#89E8DD',        // Soft teal
  'Mongoose': '#6DD0B1',        // Medium green
  'Arugula': '#24C0A7',         // Vibrant teal
  'Beetroot Bordeaux': '#36AD68'// Deeper green
};

function updateChart(chart, labels, data, label, type = 'bar') {
  chart.data.labels = labels;
  chart.data.datasets[0].label = label;
  chart.data.datasets[0].data = data;

  if (chart === plantVarietyChart) {
    chart.data.datasets[0].backgroundColor = labels.map(l => plantColorMap[l] || '#CCCCCC');
  } else if (type === 'pie') {
    chart.data.datasets[0].backgroundColor = labels.map(l => leafColorMap[l] || '#CCCCCC');
  }

  chart.update();
}


//  Analytics Extraction
function extractAnalyticsData() {
  const rows = [...document.querySelectorAll('#dataTable tbody tr')];
  const dateFilter = document.getElementById('filter-date').value;
  const floorFilter = document.getElementById('filter-floor').value;
  const plantFilter = document.getElementById('filter-plant').value;

  let filteredData = data;

  if (dateFilter) filteredData = filteredData.filter(d => d.date === dateFilter);
  if (floorFilter) filteredData = filteredData.filter(d => d.floor == floorFilter);
  if (plantFilter) filteredData = filteredData.filter(d => d.plant === plantFilter);

  const plantCounts = {};
  const leafColors = {};
  const growthStages = {};
  const heightPoints = [];
  const heightLabels = [];
  const humidityValues = [];
  const temperatureValues = [];
  const timeLabels = [];

  const sorted = [...filteredData].sort((a, b) => new Date(a.timestamp) - new Date(b.timestamp)).slice(-6);

  sorted.forEach(entry => {
    timeLabels.push(entry.date);
    temperatureValues.push(entry.temperature);
    humidityValues.push(entry.humidity);
  });
  // If no plant is chosen, default to the first plant alphabetically
  let selectedPlant = plantFilter;
  if (!selectedPlant) {
    const allPlants = [...new Set(filteredData.map(d => d.plant))].sort();
    selectedPlant = allPlants[0]; // Pick the first plant
  }

  filteredData.forEach(entry => {
    plantCounts[entry.plant] = (plantCounts[entry.plant] || 0) + 1;
    leafColors[entry.leafColor] = (leafColors[entry.leafColor] || 0) + 1;
    growthStages[entry.stage] = (growthStages[entry.stage] || 0) + 1;

    if (entry.plant === selectedPlant) {
      heightPoints.push(entry.height);
      heightLabels.push(entry.date);
    }
  });

  updateChart(plantVarietyChart, Object.keys(plantCounts), Object.values(plantCounts), 'Plant Variety');
  updateChart(temperatureChart, timeLabels, temperatureValues, 'Temperature (°C)', 'line');
  updateChart(humidityChart, timeLabels, humidityValues, 'Humidity (%)', 'line');
  updateChart(leafColorChart, Object.keys(leafColors), Object.values(leafColors), 'Leaf Colors', 'pie');
  updateChart(growthStageChart, Object.keys(growthStages), Object.values(growthStages), 'Growth Stages');
  updateChart(
    heightOverTimeChart,
    heightLabels,
    heightPoints,
    `Height Over Time (${selectedPlant})`,
    'line'
  );
}


// Filter Dropdowns
function populateFilters() {
  const dates = [...new Set(data.map(d => d.date))];
  const floors = [...new Set(data.map(d => d.floor))];
  const plants = [...new Set(data.map(d => d.plant))];

  const dateSelect = document.getElementById('filter-date');
  const floorSelect = document.getElementById('filter-floor');
  const plantSelect = document.getElementById('filter-plant');

  [dateSelect, floorSelect, plantSelect].forEach(select => {
    while (select.children.length > 1) select.removeChild(select.lastChild);
  });

  dates.forEach(val => dateSelect.append(new Option(val, val)));
  floors.forEach(val => floorSelect.append(new Option(val, val)));
  plants.forEach(val => plantSelect.append(new Option(val, val)));
}

// Trigger chart update on filter change
['filter-date', 'filter-floor', 'filter-plant'].forEach(id => {
  document.getElementById(id).addEventListener('change', extractAnalyticsData);
});


// Initialize Page
document.addEventListener('DOMContentLoaded', async () => {
  await fetchData();
  renderTable();
  renderPagination();
  createCharts();
  populateFilters();
  extractAnalyticsData();

});
