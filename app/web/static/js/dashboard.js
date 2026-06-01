/**
 * 仪表盘数据交互
 * 从API获取数据并渲染图表
 */

document.addEventListener('DOMContentLoaded', function () {
    loadDashboardStats();
    loadSentimentChart();
    loadSentimentPie();
    loadKeywordsChart();
    loadTopicClusterChart();
});

async function fetchJSON(url) {
    try {
        const resp = await fetch(url);
        if (!resp.ok) return null;
        return await resp.json();
    } catch (e) {
        console.warn('Fetch failed:', url, e);
        return null;
    }
}

async function loadDashboardStats() {
    const videos = await fetchJSON('/api/v1/videos/?page=1&page_size=1');
    const comments = await fetchJSON('/api/v1/comments/?page=1&page_size=1');

    if (videos) {
        document.getElementById('stat-videos').textContent = videos.total || 0;
    }
    if (comments) {
        document.getElementById('stat-comments').textContent = comments.total || 0;
    }
}

async function loadSentimentChart() {
    const data = await fetchJSON('/api/v1/analysis/sentiment');
    const chart = echarts.init(document.getElementById('chart-sentiment'));

    if (!data || data.status === 'no_data') {
        chart.setOption({ title: { text: '暂无情感分析数据', left: 'center' } });
        return;
    }

    const trendData = data.trend_data || [];
    const dates = [...new Set(trendData.map(d => d.time))].sort();
    const positive = dates.map(d => trendData.filter(t => t.time === d && t.label === 'positive').length);
    const neutral = dates.map(d => trendData.filter(t => t.time === d && t.label === 'neutral').length);
    const negative = dates.map(d => trendData.filter(t => t.time === d && t.label === 'negative').length);

    chart.setOption({
        tooltip: { trigger: 'axis' },
        legend: { data: ['正面', '中性', '负面'] },
        xAxis: { type: 'category', data: dates },
        yAxis: { type: 'value' },
        series: [
            { name: '正面', type: 'line', data: positive, smooth: true },
            { name: '中性', type: 'line', data: neutral, smooth: true },
            { name: '负面', type: 'line', data: negative, smooth: true }
        ]
    });
}

async function loadSentimentPie() {
    const data = await fetchJSON('/api/v1/analysis/sentiment');
    const chart = echarts.init(document.getElementById('chart-sentiment-pie'));

    if (!data || data.status === 'no_data') {
        chart.setOption({ title: { text: '暂无数据', left: 'center' } });
        return;
    }

    chart.setOption({
        tooltip: { trigger: 'item' },
        series: [{
            type: 'pie',
            radius: ['40%', '70%'],
            data: [
                { value: Math.round((data.positive_ratio || 0) * 100), name: '正面' },
                { value: Math.round((data.neutral_ratio || 0) * 100), name: '中性' },
                { value: Math.round((data.negative_ratio || 0) * 100), name: '负面' }
            ]
        }]
    });
}

async function loadKeywordsChart() {
    const data = await fetchJSON('/api/v1/analysis/keywords');
    const chart = echarts.init(document.getElementById('chart-wordcloud'));

    if (!data || data.status === 'no_data') {
        chart.setOption({ title: { text: '暂无关键词数据', left: 'center' } });
        return;
    }

    const keywords = (data.keywords || []).slice(0, 20);
    chart.setOption({
        tooltip: { trigger: 'item' },
        series: [{
            type: 'graph',
            layout: 'force',
            roam: true,
            data: keywords.map((k, i) => ({
                name: k.word,
                value: k.count,
                symbolSize: Math.min(60, 10 + k.count * 2),
            })),
            force: { repulsion: 100 }
        }]
    });
}

async function loadTopicClusterChart() {
    const data = await fetchJSON('/api/v1/analysis/topic-cluster');
    const chart = echarts.init(document.getElementById('chart-cluster'));

    if (!data || data.status === 'no_data') {
        chart.setOption({ title: { text: '暂无话题聚类数据', left: 'center' } });
        return;
    }

    const scatter = data.scatter_data || [];
    chart.setOption({
        tooltip: { trigger: 'item' },
        xAxis: { type: 'value' },
        yAxis: { type: 'value' },
        series: [{
            type: 'scatter',
            data: scatter.map(s => [s.x, s.y]),
            symbolSize: 10
        }]
    });
}
