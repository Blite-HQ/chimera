import { FileText, Upload } from 'lucide-react';
import React, { useRef } from 'react';

import { EmptyState } from '@/components/feedback/DataState';
import { SectionHeader } from '@/components/layout/SectionHeader';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow
} from '@/components/ui/table';

import { shortDate } from './format';

import type { ProjectFile } from '../data/schemas';

/**
 * Papers y archivos del proyecto (P10/M24).
 *
 * **Lo que esta vista promete es exactamente lo que el sistema cumple.** Un
 * archivo subido acá es un INSUMO con procedencia, no evidencia: el freeze §7
 * manda que el contenido recuperado entre como `assumption` con su
 * `ref{name, digest}`, jamás como `Attestation`. Por eso el digest está a la
 * vista y en mono — es lo que un certificado puede citar, y lo que un tercero
 * usa para comprobar que el PDF que leyó es el que el run leyó.
 *
 * El nombre se muestra pero no manda: el digest es la identidad (O3), así que
 * el mismo PDF con dos nombres es UN archivo.
 */

export interface PapersViewProps {
  readonly files: readonly ProjectFile[];
  /** Ausente ⇒ no hay backend de archivos (réplica): la zona no promete subir. */
  readonly onUpload?: (file: File) => void;
  readonly isUploading?: boolean;
  readonly uploadError?: string | null;
  readonly downloadUrl?: (digest: string) => string;
}

const KB = 1024;
const MB = KB * 1024;

function formatSize(bytes: number): string {
  if (bytes < KB) return `${bytes} B`;
  if (bytes < MB) return `${Math.round(bytes / KB)} KB`;
  return `${(bytes / MB).toFixed(1)} MB`;
}

export default function PapersView({
  files,
  onUpload,
  isUploading = false,
  uploadError = null,
  downloadUrl
}: PapersViewProps): React.ReactElement {
  const inputRef = useRef<HTMLInputElement>(null);

  const elegir = (event: React.ChangeEvent<HTMLInputElement>): void => {
    const file = event.target.files?.[0];
    if (file) onUpload?.(file);
    // Permite volver a elegir el MISMO archivo: `change` no dispara si el
    // value no cambió, así que sin esto reintentar tras un error no haría nada.
    event.target.value = '';
  };

  return (
    <section className="flex flex-col gap-4">
      <SectionHeader
        title="Papers y archivos"
        description="Literatura y archivos del proyecto — insumos con procedencia, citables por su digest."
      />

      {uploadError !== null && uploadError !== '' && (
        <Alert variant="destructive">
          <AlertDescription>{uploadError}</AlertDescription>
        </Alert>
      )}

      {onUpload === undefined ? (
        <div
          aria-disabled="true"
          className="rounded-xl border border-dashed border-border px-4 py-8 text-center text-sm text-muted-foreground"
        >
          La subida de archivos necesita el API en vivo.
          <span className="mt-1 block text-xs">
            En modo réplica no hay dónde guardar los bytes — y guardarlos en el navegador sería
            prometer una procedencia que nadie puede comprobar.
          </span>
        </div>
      ) : (
        <div className="flex flex-col items-center gap-2 rounded-xl border border-dashed border-border px-4 py-8 text-center">
          <input
            ref={inputRef}
            type="file"
            className="sr-only"
            aria-label="Archivo para subir"
            onChange={elegir}
          />
          <Button size="sm" disabled={isUploading} onClick={() => inputRef.current?.click()}>
            <Upload data-icon="inline-start" />
            {isUploading ? 'Subiendo…' : 'Subir un archivo'}
          </Button>
          <p className="text-xs text-muted-foreground">
            Se guarda por su digest: el mismo archivo dos veces es una sola entrada.
          </p>
        </div>
      )}

      {files.length === 0 ? (
        <EmptyState
          title="Todavía no hay archivos en este proyecto."
          hint="Los papers y datos que suba acá quedan citables por digest desde los runs."
        />
      ) : (
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Archivo</TableHead>
              <TableHead>Digest</TableHead>
              <TableHead>Tipo</TableHead>
              <TableHead>Tamaño</TableHead>
              <TableHead>Fecha</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {files.map(file => (
              <TableRow key={file.digest}>
                <TableCell>
                  <span className="flex items-center gap-2">
                    <FileText className="size-4 shrink-0 text-muted-foreground" aria-hidden />
                    {downloadUrl === undefined ? (
                      (file.filename ?? '(sin nombre)')
                    ) : (
                      <a
                        href={downloadUrl(file.digest)}
                        className="focus-ring rounded-sm underline-offset-4 hover:underline"
                        download={file.filename ?? file.digest}
                      >
                        {file.filename ?? '(sin nombre)'}
                      </a>
                    )}
                  </span>
                </TableCell>
                <TableCell>
                  <span className="font-mono text-xs" title={file.digest}>
                    {file.digest.slice(0, 12)}…
                  </span>
                </TableCell>
                <TableCell className="text-xs text-muted-foreground">{file.media_type}</TableCell>
                <TableCell className="text-xs">{formatSize(file.size_bytes)}</TableCell>
                <TableCell className="text-xs text-muted-foreground">
                  {shortDate(file.created_at)}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      )}
    </section>
  );
}
