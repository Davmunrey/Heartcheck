"""Textos educativos (no diagnóstico clínico)."""

DISCLAIMER_ES = (
    "HeartScan ofrece información educativa únicamente. No sustituye el consejo médico "
    "profesional, el diagnóstico ni el tratamiento. Consulte siempre a un profesional sanitario."
)


def screening_message(class_label: str, status: str) -> str:
    if status == "unknown":
        return (
            "La calidad de la señal o la confianza del análisis no permiten una lectura fiable. "
            "Repita el registro con mejor contacto de electrodos o suba una imagen más nítida."
        )
    if class_label == "noise":
        return (
            "El patrón se parece más a ruido o artefacto que a un ritmo claro. "
            "Conviene repetir el electrocardiograma o comentarlo con un profesional si hay síntomas."
        )
    if class_label == "arrhythmia" or status == "red":
        return (
            "El patrón sugiere irregularidad del ritmo o un hallazgo que conviene comentar con un profesional."
        )
    return "El patrón es compatible con un ritmo regular en este cribado; no sustituye una valoración médica."
