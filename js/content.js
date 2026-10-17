// Tutto il testo del sito. Le voci sono in ordine: è l'ordine dell'indice e del giro.
// `id` è il nome dell'oggetto nella stanza (vedi blender/room.py); "me" non ha un oggetto.
// Una voce può avere: kicker (riga piccola sotto il titolo, facoltativa), body (html), blocks (sezioni con
// titoletto, e dentro html, list o papers per le pubblicazioni), links, trick (il gioco di carte),
// azim/elev (da dove la camera guarda l'oggetto quando si apre la scheda, in gradi), focus
// ([x, y, z, raggio] da inquadrare, se non basta il contorno dell'oggetto), alt (un'altra inquadratura
// con focus/azim/elev: se clicchi più vicino al suo focus si apre la stessa scheda guardando lì).

export const LINKS = {
  instagram: { label: "instagram", url: "https://www.instagram.com/wakephul/" },
  strava: { label: "strava", url: "https://www.strava.com/athletes/67722942" },
  github: { label: "github", url: "https://github.com/wakephul" },
  scholar: { label: "google scholar", url: "https://scholar.google.com/citations?user=M7wkhTQAAAAJ&hl=it" },
  orcid: { label: "orcid", url: "https://orcid.org/0000-0002-7581-5955" },
  blog: { label: "il blog", url: "https://wakephul.wordpress.com" },
  cikubo: { label: "cikubo.it", url: "https://cikubo.it" },
  ovosodo: { label: "ovosodo.net", url: "https://www.ovosodo.net" },
  disagio: { label: "disagio in sella", url: "https://wakephul.github.io/disagio-in-sella/" },
  disagioig: { label: "disagio su instagram", url: "https://www.instagram.com/disagioinsella/" },
  musin: { label: "musin", url: "https://github.com/wakephul/musin" },
};

// I libri che mi sono piaciuti: titolo, autore e due righe mie. Finché è vuota non si vede.
const BOOKS = [
  // { title: "titolo", author: "autore", note: "perché mi è piaciuto" },
];

const doi = (d) => `https://doi.org/${d}`;
const a = (k, text) => `<a href="${LINKS[k].url}" target="_blank" rel="noopener">${text}</a>`;   // a link inside a sentence

export const ENTRIES = [
  {
    id: "me",
    title: "chi sono",
    kicker: "in breve (forse)",
    body: `
      <p>ciao, sono riccardo. nella vita reale rick, ricca, rico, rixa... online invece sono wakephul più o meno dal 2009 (la storia del nome è stupida e la sanno in pochi, va bene così). cosa faccio nella vita? faccio sport vari, studio cose e lavoro (molto più di quanto mi piacerebbe fare).</p>
      <p>alcuni dettagli del mio passato sono rimasti in giro per la stanza, come la giocoleria e la cartomagia.</p>
      <p>buona esplorazione!</p>`,
    links: ["instagram", "strava", "github"],
  },
  {
    id: "guitar",
    azim: 16, elev: 8,
    title: "la musica",
    body: `
      <p>suono la chitarra e ogni tanto scrivo qualcosa di mio. pubblicherò qualcosa? forse, ma non c'è nulla di certo in questa vita.</p>`,
  },
  {
    id: "bike",
    azim: 52, elev: 16,
    title: "la bici",
    body: `
      <p>la bici è il mio mezzo di trasporto preferito. sia per gli spostamenti di tutti i giorni, sia per i viaggi.</p>`,
    blocks: [
      {
        title: "disagio in sella",
        html: `<p>da qualche anno ormai, tutte le estati montiamo le borse sulla bici e andiamo a farci un giretto. raccogliamo alcuni tracciati ${a("disagio", "qui")} e alcune foto (oltre agli aggiornamenti in diretta) ${a("disagioig", "qui")}.</p>`,
      },
    ],
    links: ["strava", "disagio", "disagioig"],
  },
  {
    id: "shoes",
    azim: 38, elev: 30,
    title: "la corsa",
    body: `<p>la corsa mi accompagna soprattutto durante le giornate più dure, da un sacco di anni. prima fallito come ostacolista, poi come scattista, adesso allungo le distanze (così ho la scusa per andare piano).</p>`,
    links: ["strava"],
  },
  {
    id: "basketball",
    azim: 22, elev: 12,
    focus: [0.89, 1.92, -4.05, 0.42],   // il canestro: da indice e giro si guarda lui
    alt: { focus: [2.3, 0.15, -1.75, 0.3], azim: 30, elev: 34 },   // il pallone sul tappeto, se clicchi lui
    title: "il basket",
    body: `
      <p>gioco a basket da quando ero alle elementari, poi ho arbitrato per qualche anno per prendermi gli insulti di tutti i minors lombardi.</p>`,
  },
  {
    id: "juggling",
    azim: 12, elev: 46,
    title: "la giocoleria",
    body: `<p>per un periodo ho fatto roteare il diablo, poi ho provato un po' di evoluzioni con le palline. mi accompagnano in ogni trasloco e qualche volta provo a vedere se mi ricordo ancora come si fa.</p>`,
  },
  {
    id: "cards",
    azim: 36, elev: 40,
    title: "le carte",
    body: `<p>da giovane mi dilettavo con le carte, non sono mai stato bravo ma sicuramente mi divertivo. prova il gioco qui sotto :P</p>`,
    trick: true,
  },
  {
    id: "bookshelf",
    azim: 72, elev: 12,
    title: "i libri",
    body: `
      <p>qui vorrei mettere i libri che mi sono piaciuti, con qualche parola a riguardo. ci sto lavorando da un po' troppo tempo.</p>
      ${BOOKS.length ? `<ul class="books">${BOOKS.map((b) => `<li><b>${b.title}</b> <span>${b.author}</span><br>${b.note}</li>`).join("")}</ul>` : ""}
      <p>sul ripiano in basso ci sono ancora i vocabolari di latino e di greco.</p>`,
  },
  {
    id: "notebook",
    azim: 30, elev: 34,
    title: "la scrittura",
    body: `
      <p>per qualche anno ho tenuto un blog in cui scrivevo poesie, racconti brevi, qualche opinione su argomenti vari. il 2014 è stato il mio periodo più ispirato, poi l'ho un po' trascurato...</p>
      <p>comunque è ancora tutto online, a portata di curiosità.</p>`,
    links: ["blog"],
  },
  {
    id: "whiteboard",
    azim: 12, elev: 8,
    title: "la ricerca",
    body: `<p>studio il cervello, i sistemi distribuiti, il reinforcement learning e l'antifragilità dei sistemi software.</p>`,
    blocks: [
      {
        title: "il cervello",
        html: `<p>modelli e simulazioni in silico. il lavoro più grosso che ho pubblicato è sull'integrazione multisensoriale nel cervelletto; ho sviluppato musin per fare simulazioni di reti di neuroni. la trovi ${a("musin", "qui")}.</p>
          <p>adesso sto lavorando con l'EEG, per capire cosa cambia nel cervello dopo una stimolazione transcranica (tDCS).</p>`,
        papers: [
          { year: 2025, title: "Cerebellar contribution to multisensory integration: a computational modeling exploration", venue: "APL Bioengineering", url: doi("10.1063/5.0251429") },
          { year: "2021/22", title: "A computational framework to study cerebellar involvement in multisensory integration", venue: "tesi magistrale, politecnico di milano", url: "https://hdl.handle.net/10589/197260" },
        ],
      },
      {
        title: "il cloud",
        html: `<p>durante il dottorato ho insegnato (provato ad insegnare) a degli agenti di reinforcement learning a gestire in autonomia il placement di componenti sul computing continuum e l'autoscaling. il progetto si chiama FIGARO.</p>`,
        papers: [
          { year: 2026, title: "Adaptive management of computational resources through reinforcement learning", venue: "tesi di dottorato, politecnico di milano" },
          { year: 2026, title: "FIGARO: hierarchical reinforcement learning for scalable microservice management in the computing continuum", venue: "Journal of Parallel and Distributed Computing", url: doi("10.1016/j.jpdc.2026.105336") },
          { year: 2026, title: "Runtime management of artificial intelligence applications through hierarchical reinforcement learning", venue: "VALUETOOLS 2024, EAI", url: doi("10.1007/978-3-032-06818-7_14") },
          { year: 2023, title: "FIGARO: reinforcement learning management across the computing continuum", venue: "UCC 2023, ACM", url: doi("10.1145/3603166.3632565") },
        ],
      },
      {
        title: "il software antifragile",
        html: `<p>cerchiamo di fare in modo che, quando succede un imprevisto, il software ne approfitti per migliorare (di solito tende a fare il contrario). ci stiamo lavorando intensamente, abbiamo grandi idee e grandi speranze.</p>`,
      },
      {
        title: "prima ancora",
        papers: [
          { year: 2019, title: "Diversity and inclusion: buzzword or real value?", venue: "IEEE EDUCON", url: doi("10.1109/educon.2019.8725280") },
          { year: 2018, title: "Kangarucare: a homecare system for enhancing medicine adherence", venue: "CSCI", url: doi("10.1109/csci46756.2018.00283") },
          { year: 2017, title: "A wearable device for blind people to restore color perception", venue: "IEEE RTSI", url: doi("10.1109/rtsi.2017.8065974") },
        ],
      },
    ],
    links: ["scholar", "orcid", "musin"],
  },
  {
    id: "computer",
    azim: 26, elev: 18,
    title: "il lavoro",
    body: `
      <p>lavoro nell'import export di carni (curioso eh?), ma ho fondato anche cikubo, che mi piace definire "laboratorio di prodotto e ricerca", che rappresenta le mie molte anime: software su misura, consulenza, prodotti a sé stanti, supporto alla ricerca accademica.</p>
      <p>per qualche anno ho lavorato in ovosodo, dove ho imparato a districarmi tra lo sviluppo web e il design.</p>`,
    links: ["cikubo", "ovosodo", "github"],
  },
];

// La scheda che non è nell'indice: si apre cliccando la piastrella con la w, in alto sulla parete
// sinistra, sopra la libreria.
export const SECRET = {
  id: "secret",
  azim: 75, elev: 15,
  focus: [0.0, 2.15, -0.85, 0.3],
  title: "la piastrella",
  body: `<p>questa è soltanto una piastrella con una w. niente di più.</p>`,
};
