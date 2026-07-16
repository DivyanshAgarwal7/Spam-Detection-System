import React from 'react';

interface ResultBadgeProps {
  prediction: string;
  confidence?: number;
}

const resultTooltips: Record<string, string> = {
  spam: 'Unsolicited promotional or fraudulent content. These messages are often sent in bulk and may contain scams.',
  ham: 'Legitimate, non-spam content. These are genuine messages from real senders.',
  smishing: 'SMS-based phishing attempt. These messages try to trick you into revealing personal information.',
  offensive: 'Contains offensive or harmful language. This includes hate speech, harassment, or inappropriate content.',
  safe: 'Safe, non-malicious URL. This link does not appear to be dangerous.',
  malicious: 'Potentially harmful or phishing URL. This link may lead to a malicious website.'
};

const getResultColor = (prediction: string): string => {
  const colors: Record<string, string> = {
    spam: '#f44336',
    ham: '#4CAF50',
    smishing: '#FF9800',
    offensive: '#9C27B0',
    safe: '#4CAF50',
    malicious: '#f44336'
  };
  return colors[prediction.toLowerCase()] || '#757575';
};

export function ResultBadge({ prediction, confidence }: ResultBadgeProps) {
  const color = getResultColor(prediction);
  const tooltip = resultTooltips[prediction.toLowerCase()] || 'Unknown prediction type';

  return (
    <div 
      className="result-badge"
      style={{ 
        backgroundColor: color,
        color: '#fff',
        padding: '4px 12px',
        borderRadius: '20px',
        display: 'inline-block',
        fontSize: '14px',
        fontWeight: 600,
        cursor: 'help'
      }}
      title={tooltip}
    >
      {prediction}
      {confidence !== undefined && (
        <span style={{ marginLeft: '8px', fontSize: '12px', opacity: 0.8 }}>
          ({Math.round(confidence)}%)
        </span>
      )}
    </div>
  );
}