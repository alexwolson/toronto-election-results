# Luna authenticated sourcing and canonical-ID resolution: Toronto Star, 2003–2018

**Research date:** 2026-08-28  \
**Researcher:** Luna  \
**Endorser:** Toronto Star Editorial Board (`toronto_star_editorial_board`)

**Evidence packet:** [Toronto Star endorsement packages recovered through U of T Libraries](endorsement-census-star-utoronto-proquest-evidence-2026-08-28.md)  \
**Canonical tables:** `data/out/election_events.csv`, `data/out/contests.csv`, and `data/out/election_results.csv`

**Scope:** Every positive Toronto mayoral or City Council choice in the authenticated 2003, 2006, 2014 and 2018 packages currently documented in the evidence packet. This report proposes imports only; it does not edit canonical curation CSVs or release outputs.

## Resolution result

All **151** positive packet choices resolve to exactly one canonical Results `contest_id` and `candidacy_id`: **150** council rows plus the 2006 mayoral row. Matching was performed within the event, office and official ward using Unicode/diacritic-insensitive candidate-name normalization. No fuzzy or same-name fallback was used; no positive row is missing or ambiguous.

| Package | Positive rows | Explicit package observations | Proposed disposition | Evidence |
|---|---:|---|---|---|
| 2003 Council, Wards 1–21 | 19 | Ward 2 no endorsement; Ward 7 acclaimed | Import 19 facts | [ProQuest 438650442](https://www.proquest.com/docview/438650442) |
| 2003 Council, Wards 22–44 | 21 | Ward 24 acclaimed; Ward 40 no endorsement | Import 21 facts; comprehensive 2003 package | [ProQuest 1442464183](https://www.proquest.com/docview/1442464183) |
| 2006 mayor | 1 | Qualified support for David Miller | Import 1 fact | [ProQuest 439100508](https://www.proquest.com/docview/439100508) |
| 2006 Council, Wards 1–44 | 41 | Wards 39, 40 and 42 received no choice | Import 41 facts | [Wards 1–22](https://www.proquest.com/docview/439101262), [Wards 23–44](https://www.proquest.com/docview/439105757) |
| 2014 Council, Wards 1–44 | 44 | No explicit no-choice observation in packet | Import 44 facts | [Wards 1–21](https://www.proquest.com/docview/1613910148), [Wards 22–44](https://www.proquest.com/docview/1614259798) |
| 2018 Council, Wards 1–25 | 25 | Ward 7 praises Tiffany Ford but selects Anthony Perruzza | Import 25 facts | [Wards 1–12](https://www.proquest.com/docview/2119860825), [Wards 13–25](https://www.proquest.com/docview/2120126481) |

**Total proposed positive imports: 151.** The 2003 council package is now comprehensive: 40 positive choices, two explicit no-choice wards and two acclamations account for all 44 wards. The authenticated packet still does not provide a print ProQuest record for the 2014 mayoral online editorial, so that already-separate public-source lead is not included here.

## Canonical resolution tables

### 2003 Council — Wards 1–21

| Ward | Packet name | Canonical Results name | `contest_id` | `candidacy_id` | Proposed curation key |
|---:|---|---|---|---|---|
| 1 | Suzan Hall | Suzan Hall | `con_6d7f00a8037754c0a6f34579bee44966` | `can_00d113054083594398c601af68ffb66f` | `star_2003_w01_suzanhall` |
| 3 | Doug Holyday | Doug Holyday | `con_7eba7d2b2ccb57e5aa6ab13c307b2517` | `can_3f94a03e6dcc598d82f8d79d21d3bd10` | `star_2003_w03_dougholyday` |
| 4 | Gloria Lindsay Luby | Gloria Lindsay Luby | `con_2317176dbf5e5a4fab7fd65b16359ebd` | `can_7289eff0d5a85eefb326bf0da85e2dd3` | `star_2003_w04_glorialindsayluby` |
| 5 | Peter Milczyn | Peter Milczyn | `con_802f842541d15d899e8f6acf3b86ae45` | `can_6e72b441059f50d0aea1839508bed40c` | `star_2003_w05_petermilczyn` |
| 6 | Berardo Mascioli | Berardo Mascioli | `con_99b9fbf5df5f504eb0906d1c2b113d63` | `can_87764da8136359e3be08dbc887d8c487` | `star_2003_w06_berardomascioli` |
| 8 | Anthony Perruzza | Anthony Perruzza | `con_6beb6fc4da14503aa70fa94b8fe0b600` | `can_6c048d9a2df75ff2843ff90e8a3e916a` | `star_2003_w08_anthonyperruzza` |
| 9 | Maria Augimeri | Maria Augimeri | `con_3a262cc7bf83579eae79ce2032ea06d1` | `can_e1b82dacf6ba547ea5c9ec30043297ed` | `star_2003_w09_mariaaugimeri` |
| 10 | Michael Feldman | Michael Feldman | `con_18fc5604e3b45ef08d8af9b0813a1918` | `can_302514955e6a54268d565e4dcb76f228` | `star_2003_w10_michaelfeldman` |
| 11 | Frances Nunziata | Frances Nunziata | `con_ab103b8f3a915dd0b0131abea73fad5c` | `can_639e78b626f65ea8909654f9bd15ca78` | `star_2003_w11_francesnunziata` |
| 12 | Joe Renda | Joe Renda | `con_04a4bbe5ef575c72b4ec49d601f24b71` | `can_49f82b04f6c35129b9d12c53f87055e9` | `star_2003_w12_joerenda` |
| 13 | Stan Kumorek | Stan Kumorek | `con_28b9bf4109765f57a3a7923479b37af9` | `can_056cc3d109295989a6ea3b74da65352f` | `star_2003_w13_stankumorek` |
| 14 | Sylvia Watson | Sylvia Watson | `con_d100fd7c171150b8b18125987b174c3d` | `can_e969b66c2a5b599f8d41288a8de6597b` | `star_2003_w14_sylviawatson` |
| 15 | Howard Moscoe | Howard Moscoe | `con_d69bc70f79a45bf397b2a657aa858e50` | `can_4c19967cb44158558a2e3e8d90aec2b3` | `star_2003_w15_howardmoscoe` |
| 16 | Karen Stintz | Karen Stintz | `con_a060705663a15882b307108144aa8720` | `can_afe14e29075357499292a39a115bb3da` | `star_2003_w16_karenstintz` |
| 17 | Alejandra Bravo | Alejandra Bravo | `con_be3ee1a1a31f533885cbb71a268beda9` | `can_3f5ee28026dd58d49f898addc957a86f` | `star_2003_w17_alejandrabravo` |
| 18 | Adam Giambrone | Adam Giambrone | `con_4b3374ab9039564fa8ed1cedf493a0e3` | `can_82808b3e4f6e57b893db83438007ba68` | `star_2003_w18_adamgiambrone` |
| 19 | Joe Pantalone | Joe Pantalone | `con_d9eeb6c962c854b58be1e179e2168cb1` | `can_10c5c8f178975029bd84bdf4476c18f3` | `star_2003_w19_joepantalone` |
| 20 | Olivia Chow | Olivia Chow | `con_2befcc6536315440902962b270ad7f70` | `can_a3451138425b591f847f2b9754a341e7` | `star_2003_w20_oliviachow` |
| 21 | Joe Mihevc | Joe Mihevc | `con_95ddf0ee07b85a9da9038f871eeefaba` | `can_acc5d5a235b45003abd90c5770b00a0f` | `star_2003_w21_joemihevc` |

### 2003 Council — Wards 22–44

| Ward | Packet name | Canonical Results name | `contest_id` | `candidacy_id` | Proposed curation key |
|---:|---|---|---|---|---|
| 22 | Michael Walker | Michael Walker | `con_88f5ccc6b744588da3d07590c5dca974` | `can_5220e1bfad025d3eac38272d8c3a6c29` | `star_2003_w22_michaelwalker` |
| 23 | John Filion | John Filion | `con_744dd2f798b8521e8de9693750f474d2` | `can_c3f37900f3935532968d619ac325105d` | `star_2003_w23_johnfilion` |
| 25 | Jaye Robinson | Jaye Robinson | `con_47f9c6bba0165404a3fec5492a0940b3` | `can_c60c5195b8e55fd59bc3704998e33883` | `star_2003_w25_jayerobinson` |
| 26 | Jane Pitfield | Jane Pitfield | `con_ae44722023c153d7a460278c9b621435` | `can_f45218fc971f5f418367c1cf09933991` | `star_2003_w26_janepitfield` |
| 27 | Kyle Rae | Kyle Rae | `con_b5ffb866cf475caca42769d641deb4a7` | `can_98090903a50159ad8b92c4547b07e247` | `star_2003_w27_kylerae` |
| 28 | Pierre Klein | Pierre Klein | `con_727f839c8adc5531bd874edb6b663c05` | `can_20abf55f101452d6a0b36522163e4658` | `star_2003_w28_pierreklein` |
| 29 | Case Ootes | Case Ootes | `con_ec88bd40dff858e695ae9533199be499` | `can_1816cf817ed05a73a6d04e1dec8ac6a1` | `star_2003_w29_caseootes` |
| 30 | Chris Phibbs | Chris Phibbs | `con_d18675753b8f580c8834170f374d1e7c` | `can_3bdc4f9b038f5a29b96fdbbf8ba862bf` | `star_2003_w30_chrisphibbs` |
| 31 | Janet Davis | Janet Davis | `con_46f4af62ff4956f5b31ebec2e77229fa` | `can_e0131f8d5b345c81b56f5580ec851124` | `star_2003_w31_janetdavis` |
| 32 | Sandra Bussin | Sandra Bussin | `con_6d24ced99da9539aaaad476a9a2747f4` | `can_d79d773c87315351a62adbbfaaaebafa` | `star_2003_w32_sandrabussin` |
| 33 | Shelley Carroll | Shelley Carroll | `con_f3e797bac18a5e45a723ff263eafb93e` | `can_402a0e52786654fea78b0f051663141b` | `star_2003_w33_shelleycarroll` |
| 34 | Denzil Minnan-Wong | Denzil Minnan-Wong | `con_bf4b3cd94fcd50ba8d2259a6df440a17` | `can_6a9d30a6efa85372befaf5a604aa9296` | `star_2003_w34_denzilminnanwong` |
| 35 | Worrick Russell | Worrick Russell | `con_b9bda7a65c8a5e03a69746d0072f95c1` | `can_1a147cc2ba495af98e936a2272f01fbd` | `star_2003_w35_worrickrussell` |
| 36 | Brian Ashton | Brian Ashton | `con_d3ecc496be285eebb80559abe5d5f9f1` | `can_53506838096c58c4a409ca258b92dfe7` | `star_2003_w36_brianashton` |
| 37 | Michael Thompson | Michael Thompson | `con_9d346093453659cba5591e6e2efd506a` | `can_820beea0e81f5871b1582045dd276192` | `star_2003_w37_michaelthompson` |
| 38 | Glenn De Baeremaeker | Glenn De Baeremaeker | `con_61eed2bcd6ce5343bea274fe8a8028bc` | `can_d8fb8be5fd1c5e1f90edccb801d5ea70` | `star_2003_w38_glenndebaeremaeker` |
| 39 | Sherene Shaw | Sherene Shaw | `con_c49857c2f0a6591fa165be262c38930c` | `can_56d3f825daab5918b342625d91fa7fdc` | `star_2003_w39_shereneshaw` |
| 41 | Bas Balkissoon | Bas Balkissoon | `con_02e530a81bf75a6bbf6b4ca0a9ea6738` | `can_1c1054e3ef455df484dfe8f91a62e85a` | `star_2003_w41_basbalkissoon` |
| 42 | Paulette Senior | Paulette Senior | `con_5f814673ab4050e5b50e46685dbfbecb` | `can_b8bbec7dce94558da4d68ce3e5179885` | `star_2003_w42_paulettesenior` |
| 43 | David Soknacki | David Soknacki | `con_7b92b7a12bbf5240a728cbe9d42aa420` | `can_5f5b9990d2e65a2280c62e8967d5240f` | `star_2003_w43_davidsoknacki` |
| 44 | Gay Cowbourne | Gay Cowbourne | `con_abe0e1350e7856ad9a70ffdc75dd84f2` | `can_22da9483a67c5d2ba2f4316113990ad8` | `star_2003_w44_gaycowbourne` |

### 2006 Council — Wards 1–44

| Ward | Packet name | Canonical Results name | `contest_id` | `candidacy_id` | Proposed curation key |
|---:|---|---|---|---|---|
| 1 | Sonali Verma | Sonali Verma | `con_83ded5c17ed75ca788f320a13b17dd08` | `can_fea3f7ba8490521a9dc229d45ab4c40e` | `star_2006_w01_sonaliverma` |
| 2 | Kevin Mark | Kevin Mark | `con_393178f4fb765cd0bbeaa13d06dca32c` | `can_ffb19ef315715674bed4caf4f9fde84c` | `star_2006_w02_kevinmark` |
| 3 | Doug Holyday | Doug Holyday | `con_c760f9c404835bb595e5671cf893c340` | `can_359c6f0578f45ef3a4cf038ad56e5a52` | `star_2006_w03_dougholyday` |
| 4 | Gloria Lindsay Luby | Gloria Lindsay Luby | `con_1c0aff783cfb5ac995b40930229ffd15` | `can_d952200c6b98509a8f450d5ea8996147` | `star_2006_w04_glorialindsayluby` |
| 5 | Peter Milczyn | Peter Milczyn | `con_3ae0da024263524d8e13691dbeeadc88` | `can_c255829bac5c5cde8fa8a9221390b2f1` | `star_2006_w05_petermilczyn` |
| 6 | Jem Cain | Jem Cain | `con_d4f2ce7b93c75f4ca9c7bc73a4ba2a30` | `can_609cec2b4ced54ddad096b7bd1447280` | `star_2006_w06_jemcain` |
| 7 | Larry Perlman | Larry Perlman | `con_2c70fd784be55c4794f8294a723dedb9` | `can_cf645d05be7d5c2ba6dfe8ed7354f228` | `star_2006_w07_larryperlman` |
| 8 | Anthony Perruzza | Anthony Perruzza | `con_2c97298461635376899e36569d2c7be3` | `can_3c7d12b2073b512c83960997f4e7ef3c` | `star_2006_w08_anthonyperruzza` |
| 9 | Maria Augimeri | Maria Augimeri | `con_d42434b7f93353e6b9eeb64711b54648` | `can_2a3e6475274250748946d221fdbc92da` | `star_2006_w09_mariaaugimeri` |
| 10 | Michael Feldman | Michael Feldman | `con_86779f733e9f58e78227d4c49c260033` | `can_21292996478554dd9696fe813d2bee9c` | `star_2006_w10_michaelfeldman` |
| 11 | Frances Nunziata | Frances Nunziata | `con_0b8c9e853efa5e3da86b0f1eff65589e` | `can_0591973f6f6f5263883a52e798917677` | `star_2006_w11_francesnunziata` |
| 12 | Joe Renda | Joe Renda | `con_f449befd52f1538191ef612c9e711c45` | `can_f106a435ee12570b9788d3b96a9c2906` | `star_2006_w12_joerenda` |
| 13 | David Garrick | David Garrick | `con_76db9d7d1989548fadeac8b8116dc357` | `can_f4cac2c3bf3c58858742654b8c68eadc` | `star_2006_w13_davidgarrick` |
| 14 | Gord Perks | Gord Perks | `con_b4c70c0c6f465c4091dce97cbbd286b3` | `can_8beb4a28087f5a58b667f68fdc297a43` | `star_2006_w14_gordperks` |
| 15 | Ron Singer | Ron Singer | `con_9473b9c31bb55e62ac4432451881acf1` | `can_88679a0b033e5771aeaad7a3446b859a` | `star_2006_w15_ronsinger` |
| 16 | Karen Stintz | Karen Stintz | `con_77f42d0ca0a15c57a01b5579fef4625a` | `can_68c5d44aa7ca5dfa8d15c891d39bd713` | `star_2006_w16_karenstintz` |
| 17 | Alejandra Bravo | Alejandra Bravo | `con_46f7b754b02b57d0a651c417f9f0471d` | `can_ea146d9cbad959179dd04dbfb037d648` | `star_2006_w17_alejandrabravo` |
| 18 | Adam Giambrone | Adam Giambrone | `con_387d212e18c453e2a8eb298de5c374ff` | `can_5d5d216a8cb75d0f9b03794ae3482086` | `star_2006_w18_adamgiambrone` |
| 19 | Joe Pantalone | Joe Pantalone | `con_610d1afaa15d592eb956835f8fd51600` | `can_9193df3ee49d5d2b8ce3dc455922cea4` | `star_2006_w19_joepantalone` |
| 20 | Adam Vaughan | Adam Vaughan | `con_398774c449785307baa3822c581963e9` | `can_0c07293881025b1db98b02bbd55a6791` | `star_2006_w20_adamvaughan` |
| 21 | Joe Mihevc | Joe Mihevc | `con_88a17b76344c50ba9a3a118dd558c185` | `can_6bf809dc60245af896c4eda173c20f98` | `star_2006_w21_joemihevc` |
| 22 | Michael Walker | Michael Walker | `con_95ce62f8d45154c7836ec0372d2a416e` | `can_d212f925622258e8970eff24e98d7357` | `star_2006_w22_michaelwalker` |
| 23 | John Filion | John Filion | `con_1fa443b3390f5d6691f7994877cf55c8` | `can_13746a28acf45accb97ff466f44646e1` | `star_2006_w23_johnfilion` |
| 24 | Ed Shiller | Ed Shiller | `con_c90c50ce5e7c59dbaf6f3fb8efe575fd` | `can_eef06d1122375ecbb0900d4e7bebf183` | `star_2006_w24_edshiller` |
| 25 | Cliff Jenkins | Cliff Jenkins | `con_899c01be1cc951dfb79010a2fbd8ad10` | `can_f1ea2339e5d859a8bd4ec24487e8039e` | `star_2006_w25_cliffjenkins` |
| 26 | Mohamed Dhanani | Mohamed Dhanani | `con_2070d155d42250abac2e50baf8c6bf39` | `can_430c6469119652679b158b280ab7e70b` | `star_2006_w26_mohameddhanani` |
| 27 | Kyle Rae | Kyle Rae | `con_4a5af0945c9a5a01ae50e3a5ea61b3fb` | `can_e90f80334f6d5c2caf953d5e0a7f7068` | `star_2006_w27_kylerae` |
| 28 | Pam McConnell | Pam Mcconnell | `con_107ad5f6c01f5d4389c8194358534375` | `can_579934a87a3750cbbd93554642005cff` | `star_2006_w28_pammcconnell` |
| 29 | Case Ootes | Case Ootes | `con_2f8a0c46b37950fd9149d9b62f1f0142` | `can_62320820163a52c5bff17168dd311824` | `star_2006_w29_caseootes` |
| 30 | Paula Fletcher | Paula Fletcher | `con_ebbe0512549c59bc8a7a31e7ec5a59e9` | `can_5c0b674fd76f524fbcf7657aac767b51` | `star_2006_w30_paulafletcher` |
| 31 | Janet Davis | Janet Davis | `con_09d3330e921d5e53ae19007709e75bf9` | `can_2d5a50e7f10f57849dee50bd2d319190` | `star_2006_w31_janetdavis` |
| 32 | Sandra Bussin | Sandra Bussin | `con_218bbbaab66c59bc8d0d747f3ae2fb3c` | `can_3e15e3336f025aebb9b03fb269c45f24` | `star_2006_w32_sandrabussin` |
| 33 | Shelley Carroll | Shelley Carroll | `con_31d375f206cb5fe1955efa73ae9da43e` | `can_266ef7bcb50c5f74b9fdc4338627ed06` | `star_2006_w33_shelleycarroll` |
| 34 | Denzil Minnan-Wong | Denzil Minnan-Wong | `con_b1ec123602ab559c939e1aa02badcd71` | `can_8a2673db54705ab0a33640230926ff68` | `star_2006_w34_denzilminnanwong` |
| 35 | Michelle Berardinetti | Michelle Berardinetti | `con_4ead7aa21a905ad7bd1838cb33f37045` | `can_b3274fbfebff5a18b1b3fb1f64fce587` | `star_2006_w35_michelleberardinetti` |
| 36 | Brian Ashton | Brian Ashton | `con_e7325536f8e85cffa249480df8a556a2` | `can_6d96fca466345c79a7537e98e8e5fde8` | `star_2006_w36_brianashton` |
| 37 | Michael Thompson | Michael Thompson | `con_d0cb7c26d6e55def83cde1da2c9bc8c5` | `can_f6258f8db34051e7bc22919d0aaad4e3` | `star_2006_w37_michaelthompson` |
| 38 | Glenn De Baeremaeker | Glenn De Baeremaeker | `con_17c2e1a7404c5641823443ca7a6dcc10` | `can_3f84dacf17b85bdbad830258c4a975a8` | `star_2006_w38_glenndebaeremaeker` |
| 41 | Hratch Aynedjian | Hratch Aynedjian | `con_86a1f5b3235452b4a3cb3b3297e4dd51` | `can_7de65bb716635a0bb22212e998ae27c8` | `star_2006_w41_hratchaynedjian` |
| 43 | Jim Robb | Jim Robb | `con_59aa1ee85e2d51ca8dee4338d37665c2` | `can_c2eef971f9b356bc8baca5283e3f67e4` | `star_2006_w43_jimrobb` |
| 44 | Diana Hall | Diana Hall | `con_c59d97019dab554698aea8cb6eeb469a` | `can_2d2e20f4045e5748b0cd5c79e937bbbe` | `star_2006_w44_dianahall` |

### 2014 Council — Wards 1–44

| Ward | Packet name | Canonical Results name | `contest_id` | `candidacy_id` | Proposed curation key |
|---:|---|---|---|---|---|
| 1 | Idil Burale | Idil Burale | `con_5c8144ae39615a3189a3691c99c5ea4e` | `can_662f2273decb5a43a9f57b6382de1eb4` | `star_2014_w01_idilburale` |
| 2 | Andray Domise | Andray Domise | `con_622c2ee026875ae4ac60200b1559e8f6` | `can_89269c2df162570896b0aee2ef3865a4` | `star_2014_w02_andraydomise` |
| 3 | Stephen Holyday | Stephen Holyday | `con_54d4d8b5d91f5df5ba8bfdf9c61296af` | `can_4439ed92e3a352c29a780d9bcf1db5b4` | `star_2014_w03_stephenholyday` |
| 4 | John Campbell | John Campbell | `con_7acbde45d7355dbeb5327c8eff9039ed` | `can_0cfdf019986053d3b8d100be96affc39` | `star_2014_w04_johncampbell` |
| 5 | Justin Di Ciano | Justin Di Ciano | `con_5cb64f68c501559d960b05fb29843745` | `can_2845aa673c2057748b97224c2e967be7` | `star_2014_w05_justindiciano` |
| 6 | Russ Ford | Russ Ford | `con_5babda81dd6351a28a423340a03b5d8a` | `can_3187bf1e68df5989b8a6ce0b4ce3c94b` | `star_2014_w06_russford` |
| 7 | Nick Di Nizio | Nick Di Nizio | `con_0dc4d6b99efa5f32a8f36b24d080bb2d` | `can_b1a8902aa8455b3583f681a968e0f5c9` | `star_2014_w07_nickdinizio` |
| 8 | Anthony Perruzza | Anthony Perruzza | `con_2cf721e86d7a55de8cf53a0ae3f6413c` | `can_0f0b829f62e85c3594446f9eda050784` | `star_2014_w08_anthonyperruzza` |
| 9 | Maria Augimeri | Maria Augimeri | `con_004711e5bbda5d169a7774d906befd21` | `can_4ada97541b6c547ca17e6e9983ae4c30` | `star_2014_w09_mariaaugimeri` |
| 10 | James Pasternak | James Pasternak | `con_7d07021e53b35a609a75560232a15fd1` | `can_856d4ee5096e513396905274d05cf7f7` | `star_2014_w10_jamespasternak` |
| 11 | Dory Chalhoub | Dory Chalhoub | `con_fed30965855757d399c6acfbd6e6d4f4` | `can_c09f337ff61a5da3bf2b188b5a96f1ea` | `star_2014_w11_dorychalhoub` |
| 12 | Nick Dominelli | Nick Dominelli | `con_e230d66a67245cd08a806de4208d288b` | `can_800ffd8dd6d854bc88c3ea5ee3c4b920` | `star_2014_w12_nickdominelli` |
| 13 | Sarah Doucette | Sarah Doucette | `con_7ee43d0beaab558c9788d151bbd8d067` | `can_8f368351655d5313a6b3222d1db33cdf` | `star_2014_w13_sarahdoucette` |
| 14 | Gord Perks | Gord Perks | `con_5161ebd9ab2b5c55bfcd6eef433082c9` | `can_eb15951728215f8ab958874d4a9f29ef` | `star_2014_w14_gordperks` |
| 15 | Josh Colle | Josh Colle | `con_17f69fde16cb514bb16fb6e361c07fff` | `can_2f9b5c432e125d55b129256f91ee6f38` | `star_2014_w15_joshcolle` |
| 16 | Jean-Pierre Boutros | Jean-Pierre Boutros | `con_e8f16f1721ce5517977fa5bc1f660248` | `can_aa1efaa9f0b55303b2e886e6e879c478` | `star_2014_w16_jeanpierreboutros` |
| 17 | Alejandra Bravo | Alejandra Bravo | `con_b123ac953da1590ebb8bca29f5eb3bdc` | `can_1f117e090c2855258c47189504fd41ce` | `star_2014_w17_alejandrabravo` |
| 18 | Alex Mazer | Alex Mazer | `con_f59fe6995c8b528dbd3cbfbb5c3277c8` | `can_01c073b9cdc25ea49f0a393b562f8f86` | `star_2014_w18_alexmazer` |
| 19 | Mike Layton | Mike Layton | `con_c4de914fc9f15a3cab65125ee118d9c8` | `can_e99a2609a62e54cda99754cc90c5fa9c` | `star_2014_w19_mikelayton` |
| 20 | Joe Cressy | Joe Cressy | `con_a3ad5138021a51309ade19f0cbc4ebe1` | `can_ce513505751c5fccb73b36106b10ed4e` | `star_2014_w20_joecressy` |
| 21 | Joe Mihevc | Joe Mihevc | `con_643801dc921651c3a1ef5d96772fb13d` | `can_da14565abff1514b95e74ec4d75afb73` | `star_2014_w21_joemihevc` |
| 22 | Josh Matlow | Josh Matlow | `con_2d92299c561559d99eccb92c22f4eb47` | `can_5cf9914b09975c18bcc88e097347be1b` | `star_2014_w22_joshmatlow` |
| 23 | John Filion | John Filion | `con_79a0aa63063d5dd6a5a2ed28c29ecec1` | `can_4a4dfb92266c547b948edc0eb0d83d8e` | `star_2014_w23_johnfilion` |
| 24 | Dan Fox | Dan Fox | `con_e2f423965407516280c8b3af41b9f5cf` | `can_aa7f65bd26e25966b28e279f0c2145bd` | `star_2014_w24_danfox` |
| 25 | Jaye Robinson | Jaye Robinson | `con_d61412ebefff5d2b8bc9183244150abf` | `can_265d242844d856a3a67d627039398b73` | `star_2014_w25_jayerobinson` |
| 26 | Ishrath Velshi | Ishrath Velshi | `con_636fab9611ed540ebff54ad772a1827d` | `can_73cd6e86c3315d459f6f10b17de84e89` | `star_2014_w26_ishrathvelshi` |
| 27 | Kristyn Wong-Tam | Kristyn Wong-Tam | `con_13660de4bc485cc68e0744199d21cb46` | `can_0d15b129859b50f39c14ee0d4b5b0141` | `star_2014_w27_kristynwongtam` |
| 28 | Pam McConnell | Pam Mcconnell | `con_d5af05a065045bf9adaf30847252c957` | `can_dce7d4620e3c5e778884ef316336c325` | `star_2014_w28_pammcconnell` |
| 29 | Mary Fragedakis | Mary Fragedakis | `con_2f43675e2c5c59b796fafde036252ed1` | `can_0b72337b5b825b818ba68a7ade63fd0c` | `star_2014_w29_maryfragedakis` |
| 30 | Paula Fletcher | Paula Fletcher | `con_6c708130eaa15c9080cc3cd3a207f63b` | `can_05e436c873355ce9ac7cc4f41e4432dc` | `star_2014_w30_paulafletcher` |
| 31 | Janet Davis | Janet Davis | `con_639f022801275cedb8f9b4fe82711ae3` | `can_4191c6818a245d56ad3aa247bb118bd6` | `star_2014_w31_janetdavis` |
| 32 | Mary-Margaret McMahon | Mary-Margaret Mcmahon | `con_6629fd920f2b5a8d9b7959fafdd04a1a` | `can_101cffe6738b513b8c5049148f624dc5` | `star_2014_w32_marymargaretmcmahon` |
| 33 | Shelley Carroll | Shelley Carroll | `con_c57f0385335559e696305e7d4e632b40` | `can_78df6bd59a7c54a0aea5e8546dfe7165` | `star_2014_w33_shelleycarroll` |
| 34 | Denzil Minnan-Wong | Denzil Minnan-Wong | `con_d8e03f953ae157089237a1febc263587` | `can_96f21a337879501a940a9d83c4c2cca3` | `star_2014_w34_denzilminnanwong` |
| 35 | Michelle Berardinetti | Michelle Berardinetti | `con_59bfad1b37305c63a378a4614deb11ae` | `can_70142dd603c55957b30f98fa8b76a199` | `star_2014_w35_michelleberardinetti` |
| 36 | Robert Spencer | Robert Spencer | `con_b592d84a34965294a78c84c50bab4ddb` | `can_d391a62453fe5475b322529a0bfdd897` | `star_2014_w36_robertspencer` |
| 37 | Michael Thompson | Michael Thompson | `con_1e16e8a3edc55c77847b36d881fb8fe7` | `can_3ec20907e72051b0a0ab7e5b9e924482` | `star_2014_w37_michaelthompson` |
| 38 | Glenn De Baeremaeker | Glenn De Baeremaeker | `con_c8a9dfe07ee5545eb20e21d12773c57e` | `can_4db5ff0e51715d63897aa99429aa66ac` | `star_2014_w38_glenndebaeremaeker` |
| 39 | Franco Ng | Franco Ng | `con_350f0c58a79a574d926206857445b2d9` | `can_20f2c9e1238a579199f8d1f7059f008f` | `star_2014_w39_francong` |
| 40 | Norm Kelly | Norm Kelly | `con_e3f1226fd27e5ec6bf5d96a8439cc26a` | `can_397f372cc6d15e01a3a8dd86c2659956` | `star_2014_w40_normkelly` |
| 41 | Chin Lee | Chin Lee | `con_82f64d71deda5204bf8ba5ab710c21e6` | `can_79eb33c643155fd58f1a523d8cee24eb` | `star_2014_w41_chinlee` |
| 42 | Neethan Shan | Neethan Shan | `con_222bdce34cf75bbeb159589e8f46045b` | `can_1b2e5192cb9552c08e983fae4c79036a` | `star_2014_w42_neethanshan` |
| 43 | Paul Ainslie | Paul Ainslie | `con_4e3ebb6b13cb5d2396519f9df6fbdf4b` | `can_2f7d5d43e5c958a598ed4b02de07da90` | `star_2014_w43_paulainslie` |
| 44 | Diana Hall | Diana Hall | `con_4e432b136b83537fb08e7e8485f4949c` | `can_c7df068f3b2f55b996869eef64e44f66` | `star_2014_w44_dianahall` |

### 2018 Council — Wards 1–25

| Ward | Packet name | Canonical Results name | `contest_id` | `candidacy_id` | Proposed curation key |
|---:|---|---|---|---|---|
| 1 | Carol Royer | Carol Royer | `con_922d425132ad5243b459c0ca40a6dcd9` | `can_f9e0ac6db5085ecb8f61d5e3ac3fb273` | `star_2018_w01_carolroyer` |
| 2 | John Campbell | John Campbell | `con_3fc9df4b254c5eb6a2a7fb629a124bfb` | `can_c2dcebb36674540fb4ff568b9601a8f4` | `star_2018_w02_johncampbell` |
| 3 | Amber Morley | Amber Morley | `con_612115bf42b450d3aeb63bb430d3aec9` | `can_a4e55da62ed2509cb497ad0bfd65c11f` | `star_2018_w03_ambermorley` |
| 4 | Gord Perks | Gord Perks | `con_f961284da53f5a38ba3a20e7e998ef4f` | `can_f016d26c42dc5073b6e91d974223d0a7` | `star_2018_w04_gordperks` |
| 5 | Lekan Olawoye | Lekan Olawoye | `con_ac347f98e5715159b3adecf8debcbde8` | `can_467ce1971c8b595a88cebb67edda463a` | `star_2018_w05_lekanolawoye` |
| 6 | Maria Augimeri | Maria Augimeri | `con_849867f583195ad38c77941612883bd9` | `can_4eec1f4fc03c5c2192fa031a86b3420d` | `star_2018_w06_mariaaugimeri` |
| 7 | Anthony Perruzza | Anthony Perruzza | `con_990816d2030b592787bdf4a19382627f` | `can_6dfeac63c0665cf483c6ac6a4934541e` | `star_2018_w07_anthonyperruzza` |
| 8 | Mike Colle | Mike Colle | `con_caa23fae586656b2bab11ee711073a2c` | `can_4f560ce4f469526a9aead47e762a7cd1` | `star_2018_w08_mikecolle` |
| 9 | Ana Bailão | Ana Bailão | `con_55f5230db0d85c499ce7cea0ce379f5f` | `can_a9d93ea575e9511aad1985615dbd47f9` | `star_2018_w09_anabailao` |
| 10 | Joe Cressy | Joe Cressy | `con_2865d31031005dd897904c3f07e4d039` | `can_c17e828fbf045e0087095cfa28321105` | `star_2018_w10_joecressy` |
| 11 | Mike Layton | Mike Layton | `con_810611751acb5e86ab30b3277e7e6dad` | `can_aa928563d472570d901401bff637b922` | `star_2018_w11_mikelayton` |
| 12 | Josh Matlow | Josh Matlow | `con_8b4a03ef5a3c55c4ab20662c886b31a7` | `can_959affa9be1555e5bc0612838e927027` | `star_2018_w12_joshmatlow` |
| 13 | Kristyn Wong-Tam | Kristyn Wong-Tam | `con_3a43982e2a0450b2a3f4c5241f6965d8` | `can_c370bbf8fd765d9694fd4f089ba3d462` | `star_2018_w13_kristynwongtam` |
| 14 | Paula Fletcher | Paula Fletcher | `con_1b8d99f619f758efb737805a20bcf6fb` | `can_d7591ea7a10b549e97f6a6ec33e194d6` | `star_2018_w14_paulafletcher` |
| 15 | Jon Burnside | Jon Burnside | `con_6a1f4d7470675d869b3b11aede0812f2` | `can_72220a1f527a5ffb9ca19e3502f58894` | `star_2018_w15_jonburnside` |
| 16 | David Caplan | David Caplan | `con_147dca9e3758595d8766dc52d11a65f4` | `can_3b00773d04365f64a37bf88fce264eaf` | `star_2018_w16_davidcaplan` |
| 17 | Shelley Carroll | Shelley Carroll | `con_7a4043e26d4256e78ee3861fb81e718a` | `can_577ddf8125b85bf18e731f150dca4600` | `star_2018_w17_shelleycarroll` |
| 18 | Lily Cheng | Lily Cheng | `con_4def6d4e85f85950babb9030e4eae0cb` | `can_4fb866c38b735acc905d3362f137997c` | `star_2018_w18_lilycheng` |
| 19 | Matthew Kellway | Matthew Kellway | `con_45eb3e143f1b5492b4652498c957ed6b` | `can_8702c409b44c56869788d0fcb7ee8999` | `star_2018_w19_matthewkellway` |
| 20 | Suman Roy | Suman Roy | `con_6fd864aec40c5bbc9f3eb32d2e9e4379` | `can_6f9166ebde925b05ba83e45820107b7b` | `star_2018_w20_sumanroy` |
| 21 | Michael Thompson | Michael Thompson | `con_16fad19349255393a28639cd62e83ae3` | `can_44edb32c95a155788c97ba51aab252a9` | `star_2018_w21_michaelthompson` |
| 22 | Norm Kelly | Norm Kelly | `con_c555f2e9b45051a8b960bdbb0ac6080a` | `can_4185e2b2d994537280b8eae979cfdaec` | `star_2018_w22_normkelly` |
| 23 | Felicia Samuel | Felicia Samuel | `con_c85783d7c9a4550bae21b8e14f2ff992` | `can_cd24b1b0a226537e8e6a4cc6ad03981a` | `star_2018_w23_feliciasamuel` |
| 24 | Paul Ainslie | Paul Ainslie | `con_7e6cf2fd75ba560a900bb024e72fe99c` | `can_a138036d836c5c8da46d76df542f931f` | `star_2018_w24_paulainslie` |
| 25 | Neethan Shan | Neethan Shan | `con_eeda9883ca2d57148405d41f7f5a80a4` | `can_8fba857b4440581999ddfd32c59ec62f` | `star_2018_w25_neethanshan` |

### 2006 Mayor

| Packet name | Canonical Results name | `contest_id` | `candidacy_id` | Proposed curation key |
|---|---|---|---|---|
| David Miller | David Miller | `con_5d8609e7e7f4584ea28ad032690bdae8` | `can_60df17cf5ac95996aad15c760e40ee19` | `star_2006_mayor_miller` |

## Package metadata and non-edge observations

- **2003:** Ward 2 explicitly received no endorsement; Ward 7 was acclaimed; Ward 24 was acclaimed; Ward 40 received no endorsement. Acclamations and refusals are package metadata, not candidate endorsement edges.
- **2006:** Wards 39, 40 and 42 explicitly received no choice. These observations do not create negative candidate rows.
- **2018 Ward 7:** Tiffany Ford is praised as a potentially compelling progressive voice, but the article directs electoral support to Anthony Perruzza. Only Perruzza is proposed.
- **2014 mayor:** The authenticated packet did not recover a print ProQuest record for the online John Tory editorial. No 2014 mayoral import is proposed by this report.

## Name and identity audit

Every positive packet choice matched exactly one canonical candidacy within its event and ward. No candidate record is missing and no row produced multiple in-scope matches.

- 2006 Ward 28 and 2014 Ward 28: packet `Pam McConnell`; Results display name `Pam Mcconnell` (capitalization only).
- 2014 Ward 32: packet `Mary-Margaret McMahon`; Results display name `Mary-Margaret Mcmahon` (capitalization only).
- 2018 Ward 9: `Ana Bailão` preserves its diacritic in the canonical row.
- The 2003 Wards 22–44 scanned companion introduces no unresolved spelling or identity anomaly.

## Import proposal

For each row Terra validates, propose one curation record with:

- `review_state=confirmed`
- `endorsement_kind=editorial_choice`
- `date_precision=day`
- `source_type=publisher_editorial_authenticated_archive`
- the row’s canonical `contest_id` and `candidacy_id`
- the relevant ProQuest URL from the package table above

Use package publication dates from the evidence packet: 2003-11-07 (Wards 1–21), 2003-11-08 (Wards 22–44), 2006-11-10 (mayor), 2006-11-08 and 2006-11-09 (council), 2014-10-20 and 2014-10-21 (council), and 2018-10-15 and 2018-10-16 (council).

## Handoff to Terra

Terra should independently validate the 151 row resolutions, package language and publication dates before canonical curation changes. Preserve all explicit no-choice/acclamation statements and the 2018 Tiffany Ford praise/Anthony Perruzza choice distinction as metadata, not endorsement edges.
