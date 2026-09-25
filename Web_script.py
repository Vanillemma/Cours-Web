#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Analyse un fichier de logs web Apache/Nginx compressé en .gz.

Le script :
- sélectionne les requêtes GET vers /assur/am24... et /cyberpme/cyb... ;
- limite l'analyse à une fenêtre temporelle ;
- compte les accès par IP et par ressource ;
- indique si une ressource a été consultée avant 11:15 ou après 11:30 ;
- applique les contraintes de longueur de l'exercice ;
- exporte les résultats dans un fichier JSON.
"""

from __future__ import annotations

import argparse
import gzip
import json
import re
import sys
from collections import defaultdict
from datetime import datetime, time
from pathlib import Path
from typing import DefaultDict

# ---------------------------------------------------------------------------
# Configuration de l'exercice
# ---------------------------------------------------------------------------

ASSUR_PREFIX = "/assur/am24"
CYBER_PREFIX = "/cyberpme/cyb"

ASSUR_VALID_LENGTH = 23
CYBER_VALID_LENGTH = 27

BEFORE_LIMIT = time(11, 15)
AFTER_LIMIT = time(11, 30)

DEFAULT_START = "2025-11-03T09:45:00+01:00"
DEFAULT_END = "2025-11-03T13:00:00+01:00"
DEFAULT_OUTPUT = "resultats.json"

# Exemple de ligne attendue :
# 192.0.2.1 ... [03/Nov/2025:10:15:00 +0100] "GET /assur/am24... HTTP/1.1"
REQUEST_RE = re.compile(
    r'^(\S+).*?\[([^\]]+)\]\s+"GET (/(?:assur/am24|cyberpme/cyb)[^ ]*)'
)

# Structure :
# data[ip][ressource] = [nombre_acces, avant_11h15, apres_11h30]
AccessInfo = list[int | bool]
AccessData = DefaultDict[str, DefaultDict[str, AccessInfo]]


def parse_args() -> argparse.Namespace:
    """Lit les arguments de la ligne de commande."""
    parser = argparse.ArgumentParser(
        description="Analyse un fichier de logs web compressé (.gz)."
    )
    parser.add_argument(
        "fichier",
        type=Path,
        help="Chemin du fichier .log.gz à analyser.",
    )
    parser.add_argument(
        "--debut",
        default=DEFAULT_START,
        help=f"Début de la période au format ISO 8601 (défaut : {DEFAULT_START}).",
    )
    parser.add_argument(
        "--fin",
        default=DEFAULT_END,
        help=f"Fin de la période au format ISO 8601 (défaut : {DEFAULT_END}).",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=Path(DEFAULT_OUTPUT),
        help=f"Fichier JSON de sortie (défaut : {DEFAULT_OUTPUT}).",
    )
    return parser.parse_args()


def parse_iso_datetime(value: str) -> datetime:
    """Convertit une date ISO 8601 en datetime avec fuseau horaire."""
    try:
        dt = datetime.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(
            f"Date invalide : {value!r}. "
            "Format attendu : 2025-11-03T09:45:00+01:00"
        ) from exc

    if dt.tzinfo is None:
        raise ValueError(
            f"La date {value!r} doit contenir un fuseau horaire, par exemple +01:00."
        )

    return dt


def analyse_log(fichier: Path, debut: datetime, fin: datetime) -> AccessData:
    """Analyse le fichier de logs et retourne les accès regroupés par IP."""
    data: AccessData = defaultdict(
        lambda: defaultdict(lambda: [0, False, False])
    )

    with gzip.open(fichier, "rt", encoding="utf-8", errors="replace") as log:
        for line in log:
            match = REQUEST_RE.search(line)
            if not match:
                continue

            ip, date_texte, ressource = match.groups()

            try:
                date_requete = datetime.strptime(
                    date_texte, "%d/%b/%Y:%H:%M:%S %z"
                )
            except ValueError:
                # Ligne de log avec date inattendue : on l'ignore.
                continue

            if not (debut <= date_requete <= fin):
                continue

            info = data[ip][ressource]
            info[0] = int(info[0]) + 1

            heure = date_requete.time().replace(tzinfo=None)

            if heure < BEFORE_LIMIT:
                info[1] = True

            if heure > AFTER_LIMIT:
                info[2] = True

    return data


def export_json(data: AccessData, fichier_sortie: Path) -> None:
    """Exporte les résultats dans un fichier JSON."""
    serialisable = {
        ip: {
            ressource: {
                "count": int(valeurs[0]),
                "before_1115": bool(valeurs[1]),
                "after_1130": bool(valeurs[2]),
            }
            for ressource, valeurs in ressources.items()
        }
        for ip, ressources in data.items()
    }

    with fichier_sortie.open("w", encoding="utf-8") as out:
        json.dump(
            serialisable,
            out,
            indent=2,
            ensure_ascii=False,
            sort_keys=True,
        )


def print_multi(data: AccessData, prefix: str, label: str) -> None:
    """Affiche les IP ayant accédé à plusieurs ressources d'un même type."""
    print(f"\nIP ayant accédé à plusieurs fichiers {label} :")

    trouve = False

    for ip, ressources in sorted(data.items()):
        correspondances = sorted(
            ressource
            for ressource in ressources
            if ressource.startswith(prefix)
        )

        if len(correspondances) > 1:
            trouve = True
            print(f"{ip} => {', '.join(correspondances)}")

    if not trouve:
        print("Aucune.")


def filtre_ressources_valides(data: AccessData) -> AccessData:
    """Conserve uniquement les ressources ayant la longueur attendue."""
    resultat: AccessData = defaultdict(
        lambda: defaultdict(lambda: [0, False, False])
    )

    for ip, ressources in data.items():
        for ressource, valeurs in ressources.items():
            longueur = len(ressource)

            valide_assur = (
                ressource.startswith(ASSUR_PREFIX)
                and longueur == ASSUR_VALID_LENGTH
            )
            valide_cyber = (
                ressource.startswith(CYBER_PREFIX)
                and longueur == CYBER_VALID_LENGTH
            )

            if valide_assur or valide_cyber:
                resultat[ip][ressource] = valeurs.copy()

    return resultat


def print_ips_par_ressource(data: AccessData) -> None:
    """Affiche, pour chaque ressource valide, les IP qui y ont accédé."""
    ressources_vers_ips: DefaultDict[str, set[str]] = defaultdict(set)

    for ip, ressources in data.items():
        for ressource in ressources:
            ressources_vers_ips[ressource].add(ip)

    print("\nIP par fichier valide :")

    if not ressources_vers_ips:
        print("Aucune ressource valide.")
        return

    for ressource, ips in sorted(ressources_vers_ips.items()):
        print(f"{ressource} => {', '.join(sorted(ips))}")


def main() -> int:
    args = parse_args()

    try:
        debut = parse_iso_datetime(args.debut)
        fin = parse_iso_datetime(args.fin)
    except ValueError as exc:
        print(f"Erreur : {exc}", file=sys.stderr)
        return 2

    if debut > fin:
        print(
            "Erreur : la date de début doit être antérieure à la date de fin.",
            file=sys.stderr,
        )
        return 2

    if not args.fichier.is_file():
        print(
            f"Erreur : fichier introuvable : {args.fichier}",
            file=sys.stderr,
        )
        return 1

    try:
        data = analyse_log(args.fichier, debut, fin)
    except (OSError, gzip.BadGzipFile) as exc:
        print(
            f"Erreur lors de la lecture du fichier : {exc}",
            file=sys.stderr,
        )
        return 1

    export_json(data, args.output)

    # 1) IP ayant accédé à plusieurs fichiers, sans filtre de longueur.
    print_multi(data, ASSUR_PREFIX, "d'assurance maladie")
    print_multi(data, CYBER_PREFIX, "cyber")

    # 2) Même recherche avec les contraintes de longueur de l'exercice.
    donnees_filtrees = filtre_ressources_valides(data)

    print_multi(
        donnees_filtrees,
        ASSUR_PREFIX,
        "d'assurance maladie (filtrés)",
    )
    print_multi(
        donnees_filtrees,
        CYBER_PREFIX,
        "cyber (filtrés)",
    )

    # 3) Pour chaque fichier valide, afficher les IP correspondantes.
    print_ips_par_ressource(donnees_filtrees)

    print(f"\nRésultats JSON enregistrés dans : {args.output}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
