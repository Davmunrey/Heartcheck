export const MAX_ANALYZE_FILE_SIZE = 10 * 1024 * 1024;

export function validateAnalyzeFile(file: FormDataEntryValue | null): Blob {
  if (!(file instanceof Blob)) {
    throw new Error("Falta el archivo de imagen.");
  }

  if (file.size > MAX_ANALYZE_FILE_SIZE) {
    throw new Error(
      "El archivo supera el límite de 10 MB. Selecciona una imagen más pequeña."
    );
  }

  return file;
}
