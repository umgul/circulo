# circulo

**Árboles de saber que el agente tiene que ganarse — y puede perder.**

Casi todas las memorias de agente registran lo que pasó. Esta registra en qué
se ha vuelto bueno el agente, como algo que hay que ganarse y se puede perder.

**No verifica nada por sí misma** — ver [Lo que esto NO puede hacer](#lo-que-esto-no-puede-hacer),
que es lo primero que conviene leer.

Sin dependencias. Sin E/S. Se serializa a donde ya guardes tus cosas.

> English version: [README.md](README.md)

```bash
pip install git+https://github.com/umgul/circulo.git
```

```python
from circulo import Circulo, KIND_STUDY, KIND_PRACTICE, KIND_CREATION

c = Circulo()

c.add_ring("rust", KIND_STUDY, "leí el capítulo de ownership",
           {"projects": 0.7, "contributes": 0.6, "fulfils": 0.4})

c.mastery_of("rust")
# {'topic': 'rust', 'level': 0, 'level_name': 'SPROUT', 'depth': 0.089,
#  'generativity': 0.0, 'rings': 1, 'dormant': False, 'kinds': ['study'],
#  'self_judged': 1.0, 'judges': ['self']}

c.can("rust")          # False — un capítulo no es competencia

# ...ocho sesiones construyendo con ello después:
c.mastery_of("rust")
# {'topic': 'rust', 'level': 3, 'level_name': 'CROWN', 'depth': 0.759,
#  'generativity': 0.387, 'rings': 9, 'dormant': False,
#  'kinds': ['practice', 'study'], 'self_judged': 1.0, 'judges': ['self']}
```

Todas las salidas de este README están copiadas de una ejecución real, no
escritas a mano.

---

## El problema

Las «bibliotecas de habilidades» de agente suelen funcionar así: el agente
hace algo, sale bien, se guarda la habilidad, y desde ese momento el agente
*tiene* esa habilidad. Para siempre. A pleno rendimiento. Aunque no vuelva a
hacerla nunca.

Ahí hay tres cosas mal.

**La competencia se declara, no se demuestra.** Si el código que guarda la
habilidad decide también en qué nivel está, entonces el nivel significa lo que
diga ese código. No hay un hecho sobre el que equivocarse.

**Toda evidencia vale igual.** Leer sobre sistemas distribuidos, operar uno y
diseñar uno nuevo se registran idénticamente. Así que un agente que sólo ha
leído declara la misma competencia que uno que ha construido.

**Nunca se pierde nada.** Una curva de aprendizaje que sólo sube no es
aprendizaje. Es un contador con nombre aspiracional.

## La idea

Un árbol por materia. Dos magnitudes continuas — **profundidad** y
**generatividad** — que la evidencia mueve. `level` es una *lectura* de esas
dos, recalculada tras cada cambio.

No se desbloquea nada. No puedes ascender un árbol. Sólo puedes darle
evidencia y ver dónde cae.

```
SPROUT → ROOTS → TRUNK → CROWN → FRUIT
```

`FRUIT` es el único nivel con requisito de generatividad, y la generatividad
sólo viene de hacer cosas. **No se llega leyendo**, por mucho que se lea — que
es el comportamiento que uno quiere y casi nunca tiene.

---

## Cinco reglas, y por qué existe cada una

### 1. El nivel se LEE, no se concede

```python
from circulo import read_level

read_level(depth=1.0, generativity=0.0)   # -> CROWN, no FRUIT
```

Una función pura de dos números. Sin estado, sin puerta, sin desbloqueo. Si
quieres saber por qué un agente está en un nivel, puedes calcularlo tú.

### 2. La evidencia tiene tipos, y no son iguales

| Tipo | Profundidad | Generatividad |
|---|---|---|
| `KIND_STUDY` | 0,16 | ×0,0 — entender no genera |
| `KIND_PRACTICE` | 0,20 | ×0,30 |
| `KIND_CREATION` | 0,26 | ×1,0 |
| `KIND_DISTILL` | 0,16 | ×0,30 — muchos encuentros en una sola idea |

Un tipo sin registrar se **rechaza**: no se guarda nada y el `reason` que
devuelve dice por qué. Adivinarle un peso a un tipo desconocido sería
inventar significado donde falta información, y además dejaría ese árbol
sin poder dar fruto nunca por esa vía.

### 3. Un anillo tiene que estar SENTIDO para contar

Cada evidencia lleva una lectura subjetiva:

```python
{"projects": 0.8,     # ¿proyecta hacia adelante, abre a más?
 "contributes": 0.7,  # ¿aportó a algo más allá de sí mismo?
 "satisfies": 0.6,    # ¿fue satisfactorio?
 "fulfils": 0.9}      # ¿fue autorrealizador? (el único que alimenta generatividad)
```

Cada componente vive en `[0, 1]`. Los valores fuera de rango se recortan **con
aviso**, no en silencio — una puntuación 0-100 pasada por error produciría si
no un número plausible y equivocado.

Por debajo del corte (compuesto `0,50`) **no se registra nada**: ni anillo, ni
profundidad, ni siquiera un refresco de la fecha. Esto último importa más de lo
que parece — si el trabajo hueco regara el árbol, un agente alimentado con
ruido nunca entraría en latencia y nunca olvidaría.

Los componentes que omitas **no son ceros**. Los pesos se renormalizan sobre lo
que hay, así que quien informa sólo de lo que puede leer honestamente no queda
penalizado por el silencio. Vale también para `fulfils`: omitirlo significa
*sin evidencia generativa*, que no es lo mismo que un cero medido.

¿De dónde salen esos números? De lo que puedas medir de verdad: el resultado de
un verificador, la cobertura, la reacción de un usuario, una autoevaluación. Al
paquete le da igual — lo que le importa es que no te los inventes.

### 4. Repetir consolida; no enseña

La evidencia idéntica se descuenta a la cuarta parte.

```python
for _ in range(12):
    c.add_ring("a", KIND_STUDY, "lo mismo", felt)   # profundidad: 0,13
# frente a doce evidencias distintas                 # profundidad: 0,53
```

Sin esto, un bucle que reenvía un solo éxito alcanza la maestría con un dato.

### 5. La maestría sin uso decae

```python
c.apply_forgetting()      # llámalo en un programado, o al arrancar
# {'welsh': 0.0812}       # lo que perdió cada árbol latente
```

Tras 30 días de gracia, los árboles latentes pierden un 10% de profundidad al
mes. Lo que se erosiona es la **soltura, no el recuerdo**: los anillos no se
tocan — pasaron, se quedan — exactamente como un idioma que dejas de hablar. El
vocabulario sigue ahí. La facilidad no.

---

## `None` no es nivel cero

```python
Circulo().mastery_of("cromodinámica cuántica")   # -> None
```

Una materia nunca encontrada y una encontrada pero aún no aprendida son estados
distintos. Juntarlos es como un sistema empieza a declarar una competencia base
que nunca tuvo.

---

## API

| Método | Para qué |
|---|---|
| `add_ring(topic, kind, evidence, felt, judged_by="self", **kw)` | La única operación que importa. Devuelve un informe con `reason` cuando no pasó nada |
| `mastery_of(topic)` | Lo que se ganó de verdad, con `self_judged` y `judges`. `None` si nunca se plantó |
| `can(topic, level=TRUNK)` | ¿Se ha ganado al menos esto? `False` si nunca se plantó |
| `plant(topic, planted_from, aliases)` | Registrar una materia sin evidencia |
| `resolve(topic)` | El árbol, siguiendo alias |
| `apply_forgetting(now=None)` | Que los latentes pierdan soltura |
| `trees()` | Todos |
| `to_dict()` / `from_dict(d)` | Persistencia, JSON puro |

`FELT_WEIGHTS`, `RING_FELT_FLOOR` y `DORMANCY_DAYS` son públicas e importables, por si quieres leer los pesos en vez de adivinarlos.

**`on_level_up`** es un gancho que se llama con el árbol cuando alcanza un nivel
que no tenía — úsalo para avisar al resto de tu sistema. Un gancho que revienta
se registra y se traga: un consumidor roto jamás debe destruir el aprendizaje
del que sólo tenía que enterarse.

---

## Decidir si intentar algo

```python
from circulo import MasteryLevel

if c.can("criptografia", MasteryLevel.CROWN):
    hazlo_directamente()
elif c.mastery_of("criptografia") is None:
    estudia_primero()
else:
    hazlo_con_revision()
```

---

## Como skill de Claude

En `skills/circulo/SKILL.md` hay uno listo. Cópialo a `.claude/skills/circulo/` en tu
proyecto (o a `~/.claude/skills/circulo/` para todos) y Claude lo usará cuando
la tarea toque seguir lo que un agente ha aprendido o decidir si está
capacitado para algo.

## Como módulo

Sin dependencias, sin E/S, sin hilos. Todo se serializa a JSON plano. Encaja
con cualquier bucle de agente que ya tenga un verificador: lo que te diga que
un intento salió bien es lo que debería rellenar `felt`.

### Desde un clon

No hay paso de compilacion, pero hay que decirle a Python donde esta:

```bash
git clone https://github.com/umgul/circulo.git
cd circulo
PYTHONPATH=src python examples/quickstart.py
PYTHONPATH=src python -m pytest

# PowerShell:
#   $env:PYTHONPATH = "src"; python examples/quickstart.py
# cmd.exe:
#   set PYTHONPATH=src && python examples/quickstart.py
```

(`pytest` a secas tambien funciona —`pyproject.toml` le pone la ruta— pero el
script de ejemplo no hereda eso.)

En `examples/quickstart.py` hay un ejemplo ejecutable de punta a punta.

---

## Alimentarlo con datos fiables

circulo no verifica nada, así que la calidad de un árbol es la de lo que le
metas. Tres trabajos son tuyos, y `examples/with_a_judge.py` es una receta
ejecutable de los dos primeros.

**Juzga en una segunda llamada, no en la que hizo el trabajo.** Un modelo que
puntua su propia salida en el mismo aliento infla. Usa una llamada aparte, a
temperatura baja, dándole sólo el objetivo y el artefacto —no el razonamiento
que lo produjo— contra una rúbrica fija, y díle que omitir un componente que
no puede evaluar es lo correcto y no cuesta nada. Mejor aún: juzga desde algo
observable —tests que pasaron, tasa de error, si el artefacto se reutilizó, si
sigue funcionando una semana después—. Entonces `judged_by` deja de ser
`"self"` y `self_judged` pasa a ser un número que merece leerse.

**Saca el `event_id` del objetivo raíz, no de la prosa.**

```python
def event_id_for(goal: str) -> str:
    return hashlib.sha256(goal.strip().lower().encode()).hexdigest()[:16]
```

Tres reintentos de un objetivo son un acontecimiento, por distinto que se
cuente cada uno; las mismas palabras sobre dos objetivos distintos son dos.
Si quieres emparejar por significado entre objetivos *distintos*, eso es una
búsqueda vectorial de tu lado — hazla antes de llamar y pasa el id de lo que
hayas emparejado.

**Barre el olvido cuando el agente despierta.** `apply_forgetting()` no es
automático y nadie lo llama por ti. Un agente reactivo que sólo corre cuando
hay prompt no degradará nada jamás si no lo llamas al arrancar, o por
programado.

## Lo que esto NO puede hacer

**No puede impedir que un agente se corrija sus propios deberes.** El veredicto
`felt` lo pone quien llama a `add_ring`. Si es el mismo modelo que hizo el
trabajo, tienes un circuito cerrado:

```
el agente hace X  ->  el agente juzga X  ->  sube la maestría
                  ->  el agente se fía de su maestría
```

Este paquete no va a fingir que lo resuelve — la verificación es del llamador,
y un verificador metido dentro sería una cosa más juzgándose a sí misma. Lo que
sí se niega es a que el circuito sea **invisible**:

```python
c.add_ring("parsing", KIND_PRACTICE, "lo saqué",
           felt, judged_by="pytest")          # o "human-review", "benchmark"

c.mastery_of("parsing")["self_judged"]        # 0.5
c.mastery_of("parsing")["judges"]             # ['pytest', 'self']
```

`judged_by` viene por defecto en `"self"`, que es lo honesto y también la
evidencia más débil que existe. Un árbol en CROWN con `self_judged: 1.0` y uno
juzgado por una suite de tests no son la misma afirmación, así que
`self_judged` va en la lectura de cabecera y no escondido en un detalle.

**Aliméntalo con resultados observables siempre que puedas.** Tests, latencia,
tasa de errores, si un artefacto sigue funcionando una semana después, lo que
dijo un humano. El dict `felt` es por donde entra la señal externa — para eso
está, no para el autoinforme.

**Un `NaN` en `felt` puntuaba PERFECTO.** `min(1.0, nan)` da `1.0` en
CPython, así que cuatro NaN —resultado corriente de un `0/0` aguas arriba—
construían un anillo impecable, subían el árbol de nivel y le daban
generatividad máxima. Ahora un valor que no es un número se descarta como
uno ausente, con aviso. El `inf` va igual: un infinito salido de una división
por cero no es «el máximo», es que no hay lectura. Un 250,0 finito sí es un
error de escala y se sigue recortando.

**El descuento por repetición caza cadenas idénticas, y el parafraseo lo
derrota:**

```python
"lo resolví con el enfoque A"
"resolví el problema con éxito usando el método A"    # cuenta como nueva
```

Deduplicar por significado necesita embeddings, y este paquete no tiene
dependencias a propósito. Así que cuando conozcas la identidad del
acontecimiento, dila:

```python
c.add_ring("a", KIND_PRACTICE, "lo resolví con el enfoque A", felt,
           event_id="ticket-4471")
```

El mismo `event_id` significa que es lo mismo pasando dos veces, por muy
distinto que se cuente. Decidir si dos acontecimientos *distintos* significan
lo mismo es semántica, y la semántica sigue siendo cosa de quien llama.

**La `generativity` no decae, y es una decisión.** La profundidad se erosiona
con el desuso; lo que se ha *hecho*, no. Así que `FRUIT` significa «esto ha
creado algo», no «esto sigue siendo capaz de crear» — una creación que
ocurrió no deja de haber ocurrido al cabo de un año. Si necesitas el segundo
sentido, la generatividad necesita su propia dimensión de actualidad: la
pieza a añadir es un término de fluidez al lado, no un decaimiento sobre el
registro.

**`depth` no es un contador de memoria.** Es maestría integrada y actualmente
disponible: crece con la evidencia y *decae con el desuso*. Los anillos son la
memoria y no decaen nunca. Un modelo más limpio separaría las dos cosas — una
`depth` que sólo acumula y una `fluency` que se erosiona — para que un árbol
pudiera decir *«esto lo aprendí a fondo hace ocho meses y ahora no lo manejo
con soltura»*. Esa separación es lo principal que debería traer la 0.2.0; hoy
un solo número hace los dos trabajos, y este párrafo está aquí para que el
nombre no te engañe.

## Trabajo previo, honestamente

El pariente más cercano es **Voyager** (Wang et al., 2023), que construía una
biblioteca de habilidades en Minecraft a partir de éxitos verificados.
`circulo` comparte el instinto de fondo —las habilidades se ganan por éxito
demostrado, no se declaran— y se diferencia en cuatro cosas:

- la maestría se **lee** de la evidencia acumulada en vez de ser una prueba de
  pertenencia;
- los **tipos** de evidencia pesan distinto, así que estudiar y construir no
  son el mismo acto;
- la maestría sin uso **decae**, algo raro en sistemas de agentes y la pieza
  que más probablemente te cambie el comportamiento;
- la evidencia idéntica repetida se **descuenta**, así que los bucles no pueden
  farmearla.

Si conoces trabajo que ya resuelva bien la parte del decaimiento, abre un issue
— es la pieza con la que más nos gustaría compararnos.

## Origen

Extraído de **SGICP**, una arquitectura de fenomenología computacional
construida entre 2025 y 2026, donde es el órgano que responde a «¿qué ha
aprendido este sistema de verdad, frente a qué le han dicho?».

En aquel sistema el suelo del corte no es una constante: se calibra contra la
propia historia de veredictos sentidos del agente. Aquí es un argumento del
constructor (`felt_floor`), para que puedas darle el tuyo — incluido el que
salga de `varas`, su paquete hermano.

### Usarlos juntos

No comparten código ni vocabulario a propósito, así que el pegamento es tuyo.
Dos cosas que conviene saber antes de escribirlo.

**Un canal de varas y un árbol de circulo no son lo mismo.** Un canal es una
magnitud que observas muchas veces (`latencia`, `reintentos`, `tokens`). Un
árbol es una materia en la que mejoras (`optimizacion-sql`, `rust`).
Llamarlos igual invita a enchufar uno en otro, que es justo el error de abajo.

**No metas una señal de varas dentro de `felt`.** Tienta: `is_unusual()`
devuelve algo con la forma correcta. Pero `felt` pregunta qué tal estuvo el
trabajo, e `is_unusual()` responde si un número fue raro para este agente. Una
latencia de 0,43 s en un canal muy estrecho sale como inusual y no dice nada
de la calidad de lo hecho — cáblealo y tu árbol de maestría pasará a seguir
tu propia varianza.

El uso honesto del par es secuencial, no anidado:

```python
# varas decide si esto merece una segunda mirada
if is_unusual(state, "latencia_tarea", transcurrido) is True:
    anota_para_revisar(tarea)

# circulo registra lo aprendido, juzgado en sus propios términos
if pasaron_los_tests:
    circulo.add_ring("optimizacion-sql", KIND_PRACTICE, resumen,
                     felt_de_resultado(informe), event_id=id_de(objetivo),
                     judged_by="pytest")
```

Uno dice *este momento fue raro para mí*. El otro dice *esto me ha hecho mejor
en algo*. Los dos hablan del agente, y no son la misma frase.

## Contribuir

Los tests son la doctrina. `tests/test_circulo.py` no es cobertura — cada test
es una avería que pasó de verdad, guardada ejecutable. Si cambias el
comportamiento, cambia la ley que lo describe y di qué mediste.

```bash
python -m pytest
```

## Licencia

Apache-2.0. Ver `LICENSE` y `NOTICE`.
