document.addEventListener('DOMContentLoaded', function () {
  const payloadEl = document.getElementById('dashboard-chart-data');
  if (!payloadEl || typeof ApexCharts === 'undefined') {
    return;
  }

  const payload = JSON.parse(payloadEl.textContent || '{}');
  const monthLabelsEl = document.getElementById('dashboard-month-labels');
  const monthLabelsParsed = monthLabelsEl ? JSON.parse(monthLabelsEl.textContent || '[]') : [];
  const monthLabels = Array.isArray(monthLabelsParsed) ? monthLabelsParsed : [];

  const chart1El = document.querySelector('#dashboard-chart-1');
  const chart2El = document.querySelector('#dashboard-chart-2');
  const chart3El = document.querySelector('#dashboard-chart-3');

  if (chart1El && payload.expedientesEstado) {
    const chart1 = new ApexCharts(chart1El, {
      chart: { type: 'bar', height: 280, toolbar: { show: false }, animations: { enabled: true } },
      series: [{ name: 'Expedientes', data: payload.expedientesEstado }],
      xaxis: { categories: ['Aprobado', 'En revisión', 'Rechazado', 'Borrador'] },
      colors: ['#4AA3DF'],
      dataLabels: { enabled: true },
    });
    chart1.render();
  } else if (chart1El && payload.expedienteProgreso) {
    const chart1 = new ApexCharts(chart1El, {
      chart: { type: 'donut', height: 280, animations: { enabled: true } },
      series: payload.expedienteProgreso,
      labels: ['Documentos cargados', 'Documentos pendientes'],
      colors: ['#51bb25', '#f8d62b'],
      legend: { position: 'bottom' },
    });
    chart1.render();
  }

  if (chart2El && payload.informesEstado) {
    const chart2 = new ApexCharts(chart2El, {
      chart: { type: 'donut', height: 280, animations: { enabled: true } },
      series: payload.informesEstado,
      labels: ['Aprobado', 'En revisión', 'Rechazado', 'Borrador'],
      colors: ['#51bb25', '#4AA3DF', '#dc3545', '#a927f9'],
      legend: { position: 'bottom' },
    });
    chart2.render();
  } else if (chart2El && payload.informesResumen) {
    const chart2 = new ApexCharts(chart2El, {
      chart: { type: 'bar', height: 280, toolbar: { show: false }, animations: { enabled: true } },
      series: [{ name: 'Informes', data: payload.informesResumen }],
      xaxis: { categories: ['Aprobados', 'Pendientes'] },
      colors: ['#51bb25'],
      dataLabels: { enabled: true },
    });
    chart2.render();
  }

  if (chart3El && payload.aprobacionesMes) {
    const chart3 = new ApexCharts(chart3El, {
      chart: { type: 'area', height: 280, toolbar: { show: false }, animations: { enabled: true } },
      series: [{ name: 'Aprobaciones', data: payload.aprobacionesMes }],
      xaxis: { categories: monthLabels.length ? monthLabels : ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic'] },
      colors: ['#7366ff'],
      stroke: { curve: 'smooth' },
      dataLabels: { enabled: false },
    });
    chart3.render();
  } else if (chart3El && typeof payload.cumplimiento === 'number') {
    const chart3 = new ApexCharts(chart3El, {
      chart: { type: 'radialBar', height: 280, animations: { enabled: true } },
      series: [payload.cumplimiento],
      labels: ['Cumplimiento total'],
      colors: ['#7366ff'],
      plotOptions: {
        radialBar: {
          dataLabels: {
            value: { formatter: function (val) { return `${Math.round(val)}%`; } }
          }
        }
      }
    });
    chart3.render();
  }
});
