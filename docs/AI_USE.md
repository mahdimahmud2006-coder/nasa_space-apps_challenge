# AI assistance

Codex assisted with repository structure, code, deterministic scientific workflow design, interface implementation, tests and documentation. The user supplied local NISAR HDF5 files, `IMPLEMENTATION.md` and `SKILL.md`; these guided the project specification. The workflow audited actual schema and metadata before using dataset paths, verified repeat dates/geometry, implemented numerical processing, tested it, and built the local viewer.

AI did not classify floods or landslides, generate dataset measurements, invent acquisition dates or compute visible areas in prose. NumPy/SciPy/HDF5/geospatial code generated all measurements and thresholds. The yellow scan is presentation that reveals saved computation; it is not AI inference. No LLM/API runtime, API key or remote inference is used by the demo. No source HDF5 was uploaded to an external service. Official NASA/ASF documentation informed interpretation of real diagonal GCOV power.

Main user prompt: implement the provided datasets and implementation plan. Subsequent implementation choices and limitations are recorded in the methods and evidence, including the initial zero-result unsmoothed baseline and the explicit minimal median preprocessing. This documentation records assistance honestly without implying independently validated scientific conclusions.
