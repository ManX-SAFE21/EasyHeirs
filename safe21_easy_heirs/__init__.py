# -*- coding: utf-8 -*-
"""
Easy Heirs di SAFE21

Plugin per Electrum che prepara i fogli di carta per i beneficiari e i
paper wallet. Genera indirizzi e seed BIP39 per chi non ha un indirizzo
proprio e produce i documenti da consegnare. Non legge e non modifica la
lista eredi o il testamento di nessun altro plugin, e non costruisce, non
firma e non trasmette transazioni.
"""

fullname = "Easy Heirs di SAFE21"
description = (
    "Documenti stampabili per i beneficiari dell'eredita', con generazione "
    "di indirizzi e seed BIP39 per chi non ne ha uno proprio."
)
available_for = ["qt"]
