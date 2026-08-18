"""Scent profile implementations.

Both profiles implement the emission-and-decay arithmetic specified in
``docs/mechanisms/M-01-scent-model.md`` §B, derived from the official game book
(Book v3.0.0, ch. 4 and Appendix F). Parameters are pinned by the registered documents
in ``vectors/locked_model.json``; the conformance vectors ``vectors/pheromone.json`` and
``vectors/scent_book_v3.json`` are the correctness oracle. Do not refit the printed kernel
to a closed form.
"""
