import { useState, useEffect } from 'react';
import axios from 'axios';

const History = () => {
    const [history, setHistory] = useState([]);
    const [selectedItems, setSelectedItems] = useState([]);

    const fetchHistory = async () => {
        try {
            const token = localStorage.getItem('token');
            const res = await axios.get('/api/history', {
                headers: { Authorization: `Bearer ${token}` }
            });
            setHistory(res.data.data || []);
        } catch (error) {
            console.error('Error fetching history:', error);
        }
    };

    useEffect(() => {
        fetchHistory();
    }, []);

    const handleBulkDelete = async () => {
        if (!confirm(`Delete ${selectedItems.length} item(s)?`)) return;

        try {
            const token = localStorage.getItem('token');
            await axios.delete('/api/history/bulk-delete', {
                headers: { Authorization: `Bearer ${token}` },
                data: { ids: selectedItems }
            });
            setSelectedItems([]);
            fetchHistory();
        } catch (error) {
            alert('Failed to delete items');
        }
    };

    const toggleSelect = (id) => {
        setSelectedItems(prev =>
            prev.includes(id) ? prev.filter(i => i !== id) : [...prev, id]
        );
    };

    const handleClearAll = async () => {
        if (!confirm('Are you sure you want to permanently delete ALL history?')) return;
        try {
            const token = localStorage.getItem('token');
            await axios.delete('/api/history', {
                headers: { Authorization: `Bearer ${token}` }
            });
            setSelectedItems([]);
            fetchHistory();
        } catch (error) {
            alert('Failed to clear history');
        }
    };

    const handleExportCSV = () => {
        if (history.length === 0) return;
        
        const headers = ["Query", "Prediction", "Date"];
        const rows = history.map(item => {
            const date = item.createdAt ? new Date(item.createdAt).toLocaleString() : '';
            const safeQuery = (item.query || '').replace(/"/g, '""');
            return `"${safeQuery}","${item.prediction}","${date}"`;
        });
        
        const csvContent = [headers.join(","), ...rows].join("\n");
        const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
        const url = URL.createObjectURL(blob);
        const link = document.createElement("a");
        link.setAttribute("href", url);
        link.setAttribute("download", "scan_history.csv");
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    };

    return (
        <div style={{ padding: '20px', maxWidth: '800px', margin: '0 auto' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
                <h2 style={{ margin: 0 }}>History</h2>
                <div style={{ display: 'flex', gap: '10px' }}>
                    <button 
                        onClick={handleExportCSV}
                        disabled={history.length === 0}
                        style={{
                            background: history.length === 0 ? '#9ca3af' : '#3b82f6',
                            color: 'white',
                            padding: '8px 16px',
                            border: 'none',
                            borderRadius: '6px',
                            cursor: history.length === 0 ? 'not-allowed' : 'pointer',
                            fontWeight: '600'
                        }}
                    >
                        Download CSV
                    </button>
                    <button 
                        onClick={handleClearAll}
                        disabled={history.length === 0}
                        style={{
                            background: history.length === 0 ? '#fca5a5' : '#ef4444',
                            color: 'white',
                            padding: '8px 16px',
                            border: 'none',
                            borderRadius: '6px',
                            cursor: history.length === 0 ? 'not-allowed' : 'pointer',
                            fontWeight: '600'
                        }}
                    >
                        Clear All
                    </button>
                </div>
            </div>

            {selectedItems.length > 0 && (
                <button
                    onClick={handleBulkDelete}
                    style={{
                        background: '#ef4444',
                        color: 'white',
                        padding: '8px 16px',
                        border: 'none',
                        borderRadius: '6px',
                        cursor: 'pointer',
                        marginBottom: '10px'
                    }}
                >
                    Delete Selected ({selectedItems.length})
                </button>
            )}

            {history.length === 0 ? (
                <p>No history found.</p>
            ) : (
                history.map(item => (
                    <div
                        key={item._id}
                        style={{
                            display: 'flex',
                            alignItems: 'center',
                            gap: '10px',
                            padding: '10px 0',
                            borderBottom: '1px solid #e5e7eb'
                        }}
                    >
                        <input
                            type="checkbox"
                            checked={selectedItems.includes(item._id)}
                            onChange={() => toggleSelect(item._id)}
                        />
                        <span style={{ flex: 1 }}>{item.query}</span>
                        {item.confidence != null && (
                            <div style={{ display: 'flex', alignItems: 'center', width: '120px', marginRight: '10px' }}>
                                <div style={{ 
                                    flex: 1, 
                                    height: '6px', 
                                    background: '#e5e7eb', 
                                    borderRadius: '3px',
                                    overflow: 'hidden',
                                    marginRight: '8px'
                                }}>
                                    <div style={{
                                        height: '100%',
                                        width: `${Math.min(item.confidence * 50 + 50, 100)}%`,
                                        background: item.prediction === 'spam' || item.prediction === 'malicious' 
                                            ? '#ef4444' 
                                            : item.prediction === 'smishing' 
                                                ? '#f97316' 
                                                : '#22c55e'
                                    }} />
                                </div>
                                <span style={{ fontSize: '11px', color: '#6b7280', fontWeight: '500', width: '30px', textAlign: 'right' }}>
                                    {Math.min(item.confidence * 50 + 50, 100).toFixed(0)}%
                                </span>
                            </div>
                        )}
                        <span
                            style={{
                                padding: '2px 10px',
                                borderRadius: '12px',
                                fontSize: '12px',
                                fontWeight: '600',
                                background: item.prediction === 'spam' ? '#fee2e2' : '#dcfce7',
                                color: item.prediction === 'spam' ? '#dc2626' : '#16a34a'
                            }}
                        >
                            {item.prediction}
                        </span>
                    </div>
                ))
            )}
        </div>
    );
};

export default History;