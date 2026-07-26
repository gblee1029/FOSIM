import { FileUp, RotateCcw } from "lucide-react";
import { useRef } from "react";

import { Button } from "./ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "./ui/card";

type Props = {
  onImport: (settingsCsv: string, waveformCsv: string) => void;
  onLoadSample: () => void;
  loading: boolean;
};

export function ImportPanel({ onImport, onLoadSample, loading }: Props) {
  const settingsRef = useRef("");
  const waveformRef = useRef("");
  const readFile = (file: File, assign: (value: string) => void) => {
    const reader = new FileReader();
    reader.onload = () => assign(String(reader.result ?? ""));
    reader.readAsText(file);
  };
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
            onChange={(event) => {
              const file = event.target.files?.[0];
              if (file) readFile(file, (value) => (settingsRef.current = value));
            }}
          />
        </label>
        <label className="block text-xs font-medium text-steel">
          Waveform CSV
          <input
            className="mt-1 block w-full text-xs"
            type="file"
            accept=".csv,text/csv"
            onChange={(event) => {
              const file = event.target.files?.[0];
              if (file) readFile(file, (value) => (waveformRef.current = value));
            }}
          />
        </label>
        <div className="flex gap-2">
          <Button
            className="flex-1"
            disabled={loading}
            onClick={() => onImport(settingsRef.current, waveformRef.current)}
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
