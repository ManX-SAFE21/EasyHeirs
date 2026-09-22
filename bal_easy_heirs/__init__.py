# -*- coding: utf-8 -*-
"""
Easy Heirs - SAFE21

Plugin satellite del plugin Bitcoin After Life (BAL) per Electrum.

Legge la lista beneficiari di BAL senza modificarla, genera indirizzi e seed
BIP39 per chi non ha un indirizzo proprio, e produce i documenti da
consegnare. Non costruisce, non firma e non trasmette transazioni: resta
compito di BAL.
"""

fullname = "Easy Heirs"
description = (
    "Documenti stampabili per i beneficiari dell'eredita', con generazione "
    "di indirizzi e seed BIP39 per chi non ne ha uno proprio."
)
available_for = ["qt"]
