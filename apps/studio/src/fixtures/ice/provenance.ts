/**
 * Procedencia real de los GeoJSON del ICE (D4 — honestidad de dato: dato con
 * digest + procedencia, nunca un archivo "de algún lado"). Retenida a mano
 * (no derivada en runtime — computar un sha256 en el browser no aporta acá;
 * `provenance.test.ts` es quien la audita contra el archivo en disco).
 *
 * Fuente: portal de datos abiertos del ICE (ArcGIS Hub), descarga vía la
 * API de exportación GeoJSON de cada item, retrieved 2026-07-24.
 */

export interface IceDatasetProvenance {
  readonly dataset: string;
  readonly sourceUrl: string;
  readonly itemId: string;
  readonly license: string;
  readonly retrievedAt: string;
  readonly digest: string;
  readonly featureCount: number;
}

export const SUBESTACIONES_PROVENANCE: IceDatasetProvenance = {
  dataset: 'Subestaciones — red de transmisión del ICE',
  sourceUrl: 'https://datos-ice-se.opendata.arcgis.com/datasets/f3fceca2659b4ecf8a5c2632e04aff1f',
  itemId: 'f3fceca2659b4ecf8a5c2632e04aff1f',
  license: 'ICE datos abiertos — ver UsoOpenData',
  retrievedAt: '2026-07-24',
  digest: '39bd9a3784ba4455cae0e4a07fb5198e4def1be7bb0cba69f43e637ae69afe5c',
  featureCount: 70
};

export const LINEAS_PROVENANCE: IceDatasetProvenance = {
  dataset: 'Líneas de transmisión — red del ICE',
  sourceUrl: 'https://datos-ice-se.opendata.arcgis.com/datasets/1cd1630e16144d3bbccb1bd434dc6866',
  itemId: '1cd1630e16144d3bbccb1bd434dc6866',
  license: 'ICE datos abiertos — ver UsoOpenData',
  retrievedAt: '2026-07-24',
  digest: '3f7ae3427ef3f619bdf4a27706fa43f7bec10195d0eb4ec457e05851b8720982',
  featureCount: 102
};
