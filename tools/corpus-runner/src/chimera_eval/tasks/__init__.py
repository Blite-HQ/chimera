"""Tareas concretas — donde vive la atadura al plano de verificación.

El núcleo (`chimera_eval.dataset/task/score/runner`) no importa el engine ni el
api: una tarea sí. La frontera está acá para que el runner siga siendo una
herramienta genérica y la dependencia pesada sea un extra opcional
(`chimera-eval[plane]`), no el costo de entrada.
"""
