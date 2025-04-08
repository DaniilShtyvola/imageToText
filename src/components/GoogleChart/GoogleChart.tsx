import React, { useEffect, useRef } from 'react';
import './GoogleChart.css';

type UserAnalytics = {
    username: string;
    registered_at: string;
    last_login: string;
    session_duration: number | null;
    activity_last_30_days: number;
};

interface Props {
    data: UserAnalytics[];
}

declare global {
    interface Window {
        google: any;
    }
}

const GoogleChart: React.FC<Props> = ({ data }) => {
    const chartRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        const loadGoogleCharts = () => {
            if (window.google && window.google.charts) {
                drawChart();
            } else {
                const script = document.createElement('script');
                script.src = 'https://www.gstatic.com/charts/loader.js';
                script.onload = () => {
                    window.google.charts.load('current', { packages: ['corechart'] });
                    window.google.charts.setOnLoadCallback(drawChart);
                };
                document.body.appendChild(script);
            }
        };

        const drawChart = () => {
            const chartData = new window.google.visualization.DataTable();
            chartData.addColumn('number', 'Activity Count');
            chartData.addColumn('number', 'Session Duration');
            chartData.addColumn({ type: 'string', role: 'tooltip' });

            const rows = data
                .filter((user) => user.session_duration !== null)
                .map((user) => [
                    user.activity_last_30_days,
                    user.session_duration,
                    user.username,
                ]);

            chartData.addRows(rows);

            const options = {
                title: 'Activity vs Session Duration',
                hAxis: { title: 'Activity Count (Last 30 Days)' },
                vAxis: { title: 'Session Duration (hours)' },
                legend: 'none',
                tooltip: { isHtml: true },
                pointSize: 8,
                colors: ['#3366CC'],
            };

            const chart = new window.google.visualization.ScatterChart(chartRef.current);
            chart.draw(chartData, options);
        };

        loadGoogleCharts();
    }, [data]);

    return <div
        ref={chartRef}
        style={{
            height: "400px"
        }}
    />;
};

export default GoogleChart;
