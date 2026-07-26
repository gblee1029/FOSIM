import { FileUp, RotateCcw } from "lucide-react";
import { useRef, useState } from "react";

import { Button } from "./ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "./ui/card";

type Props = {
  onImport: (settingsCsv: string, waveformCsvs: string[]) => void;
  onLoadSample: () => void;
  loading: boolean;
};

function readFile(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result ?? ""));
    reader.onerror = () => reject(reader.error ?? new Error(`Could not read ${file.name}.`));
    reader.readAsText(file);
  });
}

export function ImportPanel({ onImport, onLoadSample, loading }: Props) {
  const settingsRef = useRef("");
  const waveformCsvs = useRef<string[]>([]);
  const [waveformCount, setWaveformCount] = useState(0);

  return (
    <Card>
      <CardHeader>
        <CardTitle>CSV import</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        <label className="block text-xs font-medium text-steel">
          Settings CSV
          <input
            className="mt-1 block w-full text-xs"
            type="file"
            accept=".csv,text/csv"
            onChange={async (event) => {
              const file = event.target.files?.[0];
              if (file) settingsRef.current = await readFile(file);
            }}
          />
        </label>
        <label className="block text-xs font-medium text-steel">
          Waveform CSV files
          <input
            className="mt-1 block w-full text-xs"
            type="file"
            accept=".csv,text/csv"
            multiple
            onChange={async (event) => {
              const files = Array.from(event.target.files ?? []);
              waveformCsvs.current = await Promise.all(files.map(readFile));
              setWaveformCount(waveformCsvs.current.length);
            }}
          />
        </label>
        <p className="text-[11px] leading-4 text-slate-500">
          {waveformCount ? `${waveformCount} waveform file(s) selected.` : "Select one or more waveform CSV files."}
        </p>
        <div className="flex gap-2">
          <Button
            className="flex-1"
            disabled={loading}
            onClick={() => onImport(settingsRef.current, waveformCsvs.current)}
            type="button"
          >
            <FileUp size={16} />
            Import
          </Button>
          <Button disabled={loading} onClick={onLoadSample} type="button" variant="secondary">
            <RotateCcw size={16} />
            Sample
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
