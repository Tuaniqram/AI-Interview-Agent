import { useState, useEffect } from 'react';
import { PageHeader } from '../components/shared/PageHeader';
import { Card } from '../components/shared/Card';

const STORAGE_KEY = 'ai-interview-settings';

interface SettingsData {
  apiUrl: string;
  wsUrl: string;
  defaultQuestions: number;
  voiceInput: boolean;
  avatarAutoSpeak: boolean;
}

const defaults: SettingsData = {
  apiUrl: 'http://localhost:8000',
  wsUrl: 'ws://localhost:8000',
  defaultQuestions: 10,
  voiceInput: true,
  avatarAutoSpeak: true,
};

function loadSettings(): SettingsData {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (raw) return { ...defaults, ...JSON.parse(raw) };
  } catch {}
  return defaults;
}

function saveSettings(data: SettingsData) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(data));
}

export function Settings() {
  const [settings, setSettings] = useState<SettingsData>(loadSettings);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    setSettings(loadSettings());
  }, []);

  const update = <K extends keyof SettingsData>(key: K, value: SettingsData[K]) => {
    setSettings(prev => ({ ...prev, [key]: value }));
  };

  const handleSave = () => {
    saveSettings(settings);
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  };

  return (
    <div className="max-w-2xl">
      <PageHeader title="Settings" description="Configure application settings" />

      <div className="space-y-6">
        <Card>
          <h3 className="text-sm font-medium text-primary mb-4">General</h3>
          <div className="space-y-4">
            <div>
              <label className="block text-xs font-medium text-secondary mb-1.5">API URL</label>
              <input type="text" value={settings.apiUrl} onChange={e => update('apiUrl', e.target.value)}
                className="w-full px-3 py-2 text-sm bg-input text-primary border border-strong rounded-lg focus:outline-none focus:ring-2 focus:ring-[var(--focus-ring)] focus:border-focus font-mono" />
            </div>
            <div>
              <label className="block text-xs font-medium text-secondary mb-1.5">WebSocket URL</label>
              <input type="text" value={settings.wsUrl} onChange={e => update('wsUrl', e.target.value)}
                className="w-full px-3 py-2 text-sm bg-input text-primary border border-strong rounded-lg focus:outline-none focus:ring-2 focus:ring-[var(--focus-ring)] focus:border-focus font-mono" />
            </div>
          </div>
        </Card>

        <Card>
          <h3 className="text-sm font-medium text-primary mb-4">Interview</h3>
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <span className="text-sm text-secondary">Default Questions</span>
              <select value={settings.defaultQuestions} onChange={e => update('defaultQuestions', Number(e.target.value))}
                className="px-3 py-1.5 text-sm bg-input text-primary border border-strong rounded-lg focus:outline-none focus:ring-2 focus:ring-[var(--focus-ring)] focus:border-focus">
                <option value={5}>5 (Quick)</option>
                <option value={10}>10 (Standard)</option>
                <option value={15}>15 (Detailed)</option>
                <option value={20}>20 (Comprehensive)</option>
              </select>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm text-secondary">Voice Input</span>
              <label className="relative inline-flex items-center cursor-pointer">
                <input type="checkbox" checked={settings.voiceInput} onChange={e => update('voiceInput', e.target.checked)} className="sr-only peer" />
                <div className="w-9 h-5 bg-input peer-focus:outline-none peer-focus:ring-2 peer-focus:ring-[var(--focus-ring)] rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-inverse after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-action-primary" />
              </label>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm text-secondary">Avatar Auto-speak</span>
              <label className="relative inline-flex items-center cursor-pointer">
                <input type="checkbox" checked={settings.avatarAutoSpeak} onChange={e => update('avatarAutoSpeak', e.target.checked)} className="sr-only peer" />
                <div className="w-9 h-5 bg-input peer-focus:outline-none peer-focus:ring-2 peer-focus:ring-[var(--focus-ring)] rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-inverse after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-action-primary" />
              </label>
            </div>
          </div>
        </Card>

        <div className="flex justify-end">
          <button onClick={handleSave}
            className="px-6 py-2 text-sm font-medium text-inverse bg-action-primary rounded-lg hover:bg-action-primary-hover transition-colors">
            {saved ? 'Saved!' : 'Save Settings'}
          </button>
        </div>
      </div>
    </div>
  );
}
