# Daklekkage Eindhoven: Stormschade-check (KNMI)

Open tool die voor een **postcode en schadedatum** laat zien wat het dichtstbijzijnde KNMI-station mat:
- het hoogste uurgemiddelde van de wind;
- de zwaarste windstoot;
- de regen.

Die waarden worden vergeleken met de **stormgrens van 14 m/s (windkracht 7)** die veel verzekeraars hanteren. Eén HTML-bestand plus statische data, zonder build, tracking of cookies. Gemaakt door [daklekkageeindhoven.com](https://daklekkageeindhoven.com/), MIT-licentie.

**Gebruik de tool:** https://tyscode14.github.io/daklekkage-eindhoven/

Direct linken kan ook, bijvoorbeeld naar storm Ciarán in Eindhoven:
https://tyscode14.github.io/daklekkage-eindhoven/?locatie=5611AB&datum=2023-11-02

## Het probleem dat deze tool oplost

Bij dakschade of een daklekkage na slecht weer vraagt de verzekeraar vaak: *was het storm?* Interpolis spreekt bijvoorbeeld van storm bij **windkracht 7 of meer, een windsnelheid van 14 meter per seconde of meer, gemeten door het KNMI**. Die meting staat in de KNMI-daggegevens, maar dan moet u zelf:
- het juiste station vinden;
- een tekstbestand met tienduizenden regels doorzoeken;
- weten dat `FHX` in tienden van m/s staat en dat het uurvak in UT is.

De tool doet dat in één stap. Hij:
- zoekt het dichtstbijzijnde station met wind- én regenmetingen;
- toont de waarden van die dag en van drie dagen ervoor en erna (schade wordt vaak later ontdekt);
- zet de tijden om naar Nederlandse tijd;
- vergelijkt de regen met de 1% en 0,1% natste dagen van hetzelfde station (1991–2020);
- maakt een printbare samenvatting voor uw verzekeraar.

## Voorbeelden uit de data (station Eindhoven, 370)

| Datum | Uurgemiddelde | Windstoot | Regen |
|---|---|---|---|
| 18 feb 2022, storm Eunice | 18,0 m/s | 32,0 m/s (115 km/u) | 3,7 mm |
| 2 nov 2023, storm Ciarán | 14,0 m/s | 28,0 m/s | 4,7 mm |
| 5 jun 2022, wolkbreuk | 6,0 m/s | 11,0 m/s | 48,3 mm (24,9 mm in één uur) |

## Over de data

`scripts/build_data.py` haalt de KNMI-daggegevens (`etmgeg_<STN>.zip`) van alle stations op en schrijft:

- `data/stations.json`: stations met coördinaten, meetperiode, percentielen 1991–2020 (p99 en p99,9) en de zwaarste dagen sinds 2000;
- `data/<STN>/<JAAR>.json`: per dag `FHX, FHXH, FXX, FXXH, DDVEC, RH, RHX, RHXH`, vanaf 2000.

Eenheden zoals bij het KNMI:
- **Wind:** FHX en FXX in 0,1 m/s.
- **Neerslag:** RH en RHX in 0,1 mm; `-1` betekent minder dan 0,05 mm.
- **Uurvakken:** in UT; uurvak 1 is 00–01 UT.

Een GitHub Action (`.github/workflows/update-data.yml`) haalt de data elke dag opnieuw op en commit de wijzigingen. Het KNMI controleert de gegevens op werkdagen, dus de laatste dagen zijn voorlopig.

Het script gebruikt alleen de Python-standaardbibliotheek:

```
python scripts/build_data.py           # alles opnieuw opbouwen
python scripts/build_data.py --recent  # alleen de laatste twee jaar (nachtelijke run)
```

Postcodes en plaatsnamen worden in de browser omgezet naar coördinaten via de [PDOK Locatieserver](https://www.pdok.nl/) (open, zonder sleutel).

## Beperkingen

- **Beperkt meetnet:** het KNMI meet op tientallen stations. Lokaal kunnen windstoten en buien zwaarder of lichter zijn; de tool toont daarom altijd de afstand tot het station, en u kunt een ander station kiezen.
- **Kuststations:** stations op zee, pieren en dammen meten vaak meer wind dan landinwaarts. De tool kiest standaard een station met ook regenmetingen, wat vrijwel altijd een landstation is.
- **Geen claimbeoordeling:** de uitkomst zegt niets over het oordeel van uw verzekeraar; de polisvoorwaarden zijn leidend.

## Bronnen

- KNMI, daggegevens van het weer in Nederland: https://www.knmi.nl/nederland-nu/klimatologie/daggegevens (CC BY 4.0)
- Interpolis, stormschade (definitie storm): https://www.interpolis.nl/schade/veelvoorkomende-schades/stormschade
- PDOK Locatieserver: https://www.pdok.nl/

## Bijdragen

Issues en pull requests zijn welkom, bijvoorbeeld om de aanvullende KNMI-neerslagstations toe te voegen of een uurtabel per dag.

## Licentie

Code: MIT. Data in `data/`: afgeleid van KNMI-daggegevens, CC BY 4.0, bron KNMI.
