; rule-set-id: particion-rules@0.1.0
;
; Reglas de dominio de una particion en islas, como DATOS versionados.
; Corrección #4 (knowledge/trust/11 §1.1 / trust/04 §4 item 3): las reglas del
; dominio electrico NO se hardcodean en el verificador — entran como este
; artefacto, y el `rule_digest` de la constancia son sus BYTES EXACTOS
; (Regla 1 del anexo de canonicalizacion, igual que `policy_digest`):
; comentarios y formato son parte de lo distribuido.
;
; Formato: SMT-LIB 2 estandar, sin extensiones propias. Cada regla lleva
; `:named` porque sin nombre el unsat core no puede señalarla (trust/11 §1.4)
; — el cargador falla fuerte si falta alguno. Que sea SMT-LIB estandar es lo
; que hace del cambio de backend (Z3 hoy, cvc5 + Alethe + Carcara para la ruta
; `formal_exact` de AL4) un drop-in y no una reescritura.
;
; Alcance declarado: estas reglas se evaluan sobre los AGREGADOS de una
; particion candidata (cuantas islas, cuantas sin fuente, desbalance maximo,
; carga servida). Son las invariantes que una particion debe cumplir para ser
; siquiera considerada; NO reemplazan al verificador por ejecucion, que corre
; el flujo de potencia de verdad. De ahi el techo AL2 del adapter: esto dice
; "los agregados declarados son consistentes con el dominio", no "los
; agregados son ciertos".
;
; Unidades: potencia en MW; fracciones en [0,1]. La tolerancia y el piso de
; carga servida entran como simbolos (no como constantes hardcodeadas) porque
; son criterio del operador, no fisica — y asi viajan en el candidato,
; auditables como cualquier otro numero del claim.

(declare-fun n_islands () Int)
(declare-fun min_island_buses () Int)
(declare-fun islands_without_source () Int)
(declare-fun max_abs_imbalance_mw () Real)
(declare-fun imbalance_tolerance_mw () Real)
(declare-fun served_load_mw () Real)
(declare-fun total_load_mw () Real)
(declare-fun min_served_fraction () Real)

; Una "particion" en una sola parte no es una particion: no hay islanding que
; verificar y el resultado seria trivialmente el sistema completo.
(assert (! (>= n_islands 2) :named at_least_two_islands))

; Ninguna isla vacia: un conjunto vacio contado como isla infla `n_islands`
; sin aportar nada, y haria pasar la regla de arriba por construccion.
(assert (! (>= min_island_buses 1) :named no_empty_island))

; Toda isla necesita al menos una fuente, o no puede sostenerse sola — es LA
; condicion que separa una particion viable de un corte cualquiera del grafo.
(assert (! (= islands_without_source 0) :named source_per_island))

; El desbalance de cada isla cabe dentro de la tolerancia declarada por el
; operador (se compara el peor caso: si el maximo cabe, todos caben).
(assert (! (<= max_abs_imbalance_mw imbalance_tolerance_mw) :named power_balance))

; La carga servida no cae por debajo del piso declarado: una particion que
; "balancea" botando la mitad de la demanda cumple lo anterior y no sirve.
(assert
  (! (>= served_load_mw (* min_served_fraction total_load_mw))
     :named served_load_floor))

; Coherencia del propio candidato: no se puede servir mas carga de la que hay.
; Sin esta regla, un candidato con `served_load_mw` inflado pasaria el piso de
; arriba sin que nada lo notara.
(assert (! (<= served_load_mw total_load_mw) :named served_load_is_consistent))
