import React, { useState, useEffect } from 'react';

const WordCloud = ({ darkMode }) => {
  const [words, setWords] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetch('/api/wordcloud')
      .then(res => res.json())
      .then(data => {
        if (data.success) {
          setWords(data.data);
        } else {
          setError(data.error);
        }
        setLoading(false);
      })
      .catch(err => {
        setError(err.message);
        setLoading(false);
      });
  }, []);

  if (loading) {
    return <p className="text-gray-400 text-sm animate-pulse">Loading word cloud...</p>;
  }

  if (error) {
    return <p className="text-red-400 text-sm">⚠️ Could not load word data</p>;
  }

  if (!words || words.length === 0) {
    return <p className="text-gray-400 text-sm">No spam words data available</p>;
  }

  const maxCount = Math.max(...words.map(w => w.count));

  const getSize = (count) => {
    const minSize = 12;
    const maxSize = 48;
    const ratio = count / maxCount;
    return Math.round(minSize + ratio * (maxSize - minSize));
  };

  const getColor = (index) => {
    const colors = ['#4f46e5', '#7c3aed', '#2563eb', '#0891b2', '#059669', '#d97706', '#dc2626', '#8b5cf6'];
    return colors[index % colors.length];
  };

  return (
    <div className={`mt-4 p-4 rounded-xl border ${darkMode ? 'bg-gray-800/70 border-gray-600' : 'bg-white/60 border-gray-200'}`}>
      <h3 className="text-sm font-semibold mb-3 text-gray-600 dark:text-gray-300">🔍 Top Spam Keywords</h3>
      <div className="flex flex-wrap items-center justify-center gap-2 p-2 min-h-[120px]">
        {words.slice(0, 30).map((word, index) => (
          <span
            key={index}
            style={{
              fontSize: `${getSize(word.count)}px`,
              color: getColor(index),
              fontWeight: 'bold',
              padding: '2px 4px',
              transition: 'all 0.2s',
              cursor: 'pointer',
              opacity: 0.8 + (word.count / maxCount) * 0.2,
            }}
            className="hover:scale-110 hover:opacity-100 transition-transform"
            title={`${word.word}: ${word.count} occurrences`}
          >
            {word.word}
          </span>
        ))}
      </div>
      <p className="text-xs text-gray-400 text-center mt-2">
        Word size indicates frequency in spam messages
      </p>
    </div>
  );
};

export default WordCloud;