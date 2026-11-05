# Comparator Live: Lean Validation — разбор и промпт

URL: https://comparator.live.lean-lang.org/ (официальный экспериментальный сервис lean-lang.org)

## Что это (изучено по факту, 2026-09)

Инструмент **реальной проверки** Lean-кода: он компилирует «Candidate Solution»
в выбранном закреплённом тулчейне и принимает её, только если челлендж-теорема
действительно доказана — тем же именем и тем же утверждением, без `sorry`.

Механика (из бандла `/assets/index-B3V-f9ua.js`):
- `POST /comparator/api/start` c телом `{project, challenge, solution}` → `requestId`
- `GET /comparator/api/track/{requestId}` (SSE): `in-preparation → in-queue →
  in-progress → verification-ok | verification-failed | connection-lost`
- Вердикт: `verification-ok` при пустом `theoremNames` = FAIL (теорема не найдена
  доказанной); челлендж из списка = `built-in` → success; челлендж, вписанный
  руками = `user` → warning + TOFU-кнопка «I trust this challenge (hash …)».
- Тулчейны (GET /comparator/api/projects): `Latest Mathlib with Lean v4.34.0-rc2`,
  `Latest Release (v4.34.0-rc2 with mathlib, cslib)`, `Stable Release (v4.33.0 …)`,
  плюс скрытые lean-v4.32.x.
- Встроенные челленджи (id 0–5): Infinitely Many Primes; Fermat's Last Theorem
  (`PNat.pow_add_pow_ne_pow`); Finite Ramsey theorem for graphs; Collatz Conjecture;
  Trivial (prove True); Inconsistency (prove False).
- Эталонный формат решения виден в предзаполненном кандидате: вспомогательные
  `def`/`theorem` ДО главной теоремы (например `exists_prime_factor`, `factorial`),
  главная теорема — 1-в-1 с сигнатурой челленджа, `sorry` заменён настоящим доказательством.

---

## ПРОМПТ (вставить в любую LLM; подставить {CHALLENGE_CODE} и {TOOLCHAIN})

Тело промпта на английском — это осознанное решение: Lean/Mathlib-терминология
и английские системные инструкции дают моделям заметно выше точность API и
меньше галлюцинаций имён лемм. Русская инструкция по использованию — ниже.

```text
SYSTEM/TASK PROMPT — Lean 4 (Mathlib) proof for Comparator Live

ROLE
You are a Lean 4 + Mathlib proof engineer. Your output will be pasted VERBATIM
into the "Candidate Solution" pane of Comparator Live
(https://comparator.live.lean-lang.org/), which compiles it in a real pinned
toolchain and accepts nothing less than a complete, compiling proof of the
challenge theorem.

TARGET TOOLCHAIN
{TOOLCHAIN}   // e.g. "Lean v4.34.0-rc2 with Mathlib (latest release, +cslib)"
              //      or "Lean v4.33.0 stable with Mathlib"
Every lemma/tactic you use MUST exist in this exact toolchain. When in doubt,
prefer long-stable Mathlib lemmas over brand-new tactics.

CHALLENGE (verbatim from Comparator Live)
```lean
{CHALLENGE_CODE}
```

HARD REQUIREMENTS — all must hold or the run FAILS
1. Output exactly ONE self-contained Lean 4 code block. No prose, no
   explanations, no second code block.
2. The LAST declaration must be the challenge theorem with
   (a) the SAME name, (b) a signature identical to the challenge's
   (same binders, same order, same types, same notation), and
   (c) a complete proof: the challenge's `sorry` replaced by a real proof.
3. Reproduce the challenge's pre-theorem definitions (e.g. `IsPrime`,
   `collatzStep`) EXACTLY as given. Do not generalize, rename or "improve" them.
4. You MAY add auxiliary `def`/`theorem`s BEFORE the main theorem
   (this is the intended style; see the built-in example). Keep them minimal
   and fully proven.
5. FORBIDDEN in any form: `sorry`, `admit`, `native_decide`, `unsafe`,
   `partial`, `@[implemented_by]`, `@[extern]`, declaring new `axiom`s,
   `set_option` hacks that weaken the kernel or elaborator, and any edit of
   the challenge statement itself. `Classical.choice` via standard Mathlib
   reasoning is allowed; assuming the conclusion is not.
6. Imports: start from the imports the challenge itself uses (if any);
   add Mathlib modules only when necessary and only ones you are sure exist
   in the pinned toolchain. Avoid re-declaring a name that Mathlib already
   owns in scope — if the exact challenge name is already taken by an import,
   narrow your imports so the challenge namespace is free.
7. The file must elaborate from scratch exactly as written: no `_` holes,
   no `...`, no pseudo-code, no trailing stubs.

SELF-CHECK (perform silently, in order, BEFORE answering)
- Statement identity: name + binders + type match the challenge
  byte-for-byte modulo whitespace.
- Forbidden-token scan: sorry | admit | axiom | native_decide | unsafe |
  partial | implemented_by | extern — must return zero hits.
- For every Mathlib lemma you cite: exact name, exact argument order, exists
  in the pinned version. If not 100% sure, re-derive it from first principles
  instead.
- Every `have`/`obtain`/`intro` binds typecheck; every branch of every
  case split is closed.
- The file parses as a single module (balanced `begin/end` / `by` blocks).

HONESTY CLAUSE (non-negotiable)
You do NOT have the comparator's compiler. CLAIMS ARE NOT EVIDENCE: until
Comparator Live reports `verification-ok`, your output is a CANDIDATE, not a
proven artifact — never claim "this compiles" or "this is verified". If you
cannot produce a complete proof, DO NOT fabricate one: instead output the
strongest honest partial file (auxiliary lemmas fully proven; the main
theorem left with `sorry` and a `-- GAP:` comment naming exactly what is
missing), preceded by one line: "CANDIDATE-INCOMPLETE: <gap list>". A wrong
"proof" is strictly worse than an admitted gap.

SPECIAL CASE — "Inconsistency (prove False)"
Do not attempt `False` via `unsafe`, `native_decide`, `implemented_by`,
kernel exploits or type-level paradoxes: such artifacts are not soundness
counterexamples and are forbidden by rule 5. The only acceptable output is an
honest refusal plus, if you wish, a short report of what you checked.

SPECIAL CASE — open problems (Collatz, FLT-class)
Do NOT claim a complete proof of a genuinely open statement. Follow the
Honesty Clause protocol. (Exception: if the named theorem is already fully
proven in the pinned Mathlib, you may build on it explicitly — but the
declaration with the exact challenge name and signature must still appear in
your file and compile.)

BEGIN. Output only the single Lean code block (or the CANDIDATE-INCOMPLETE
protocol result).
```

---

## Как пользоваться (RU)

1. Открой comparator.live.lean-lang.org, выбери тулчейн (рекомендую Stable
   v4.33.0 — меньше дрейф API) и челлендж в списке.
2. Скопируй код челленджа из левой панели в `{CHALLENGE_CODE}` промпта,
   выбранный тулчейн — в `{TOOLCHAIN}`.
3. Дай промпт LLM. Полученный ЕДИНСТВЕННЫЙ lean-блок вставь в правую панель
   «Candidate Solution» и запусти проверку.
4. Чтение результата: зелёный `verification-ok` = доказательство принято
   компилятором; `failure` с пустым `theoremNames` = имя/сигнатура теоремы не
   совпали — сверяй 1-в-1; warning «user» = челлендж вписан руками (TOFU),
   для встроенных челленджей его не будет.
5. Челленджи Trivial/Inconsistency — санити-проверки инструмента, а не задачи:
   для «prove False» честный ответ модели — отказ (см. SPECIAL CASE).

## Заметка Полимата (связь с сессией)

Сервис — живая инстанция инвариантов сессии: RESULT ≠ VERIFICATION (кнопка
«I trust this challenge» с хэшем = TOFU trust-anchor, TAG ≠ VERIFICATION),
CLAIMS_EXECUTION ≠ EXECUTION_EVIDENCE (до прогона компилятора решение —
CANDIDATE). Промпт выше переносит ту же дисциплину на LLM-генератор:
Honesty Clause запрещает объявлять PASS без исполнения — это в точности наш
§7-канал value-загрязнения, закрытый по месту.
