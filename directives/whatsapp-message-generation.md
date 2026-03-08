# WhatsApp Message Generation Workflow

## Overview

This directive describes the workflow for generating WhatsApp promotional messages for GDG Londrina events and newsletters. Each generation produces 2 alternative message options for the user to choose from.

## Message Types

### Pre-Event Messages

Use these before an event happens to drive registrations:

| Type | When to Use | Goal |
|------|-------------|------|
| **Event Announcement** | When event is first announced | Inform and excite about the event |
| **Speaker Spotlight** | 1-2 weeks before event (one per speaker) | Build credibility and curiosity about specific talks |
| **Reminder** | 1-2 days before event | Create urgency and FOMO |

### Post-Event Messages

Use after the event to promote content:

| Type | When to Use | Goal |
|------|-------------|------|
| **Newsletter Promo** | After newsletter is published | Drive clicks to read the full newsletter |

## Output Format

Each generation produces 2 alternatives:

```markdown
<!-- ALTERNATIVAS DE WHATSAPP -->

## Opcao 1 (Recomendada)
[complete message]

---

## Opcao 2
[complete message]

---
<!-- FIM DAS ALTERNATIVAS -->
```

## Input Requirements

### Event Announcement / Reminder

```json
{
  "titulo": "GDG Londrina Meetup Novembro 2025",
  "data": "29/11 (sabado)",
  "horario": "9h",
  "local": "Unicesumar Londrina",
  "link_inscricao": "https://www.sympla.com.br/...",
  "palestras": [
    {
      "titulo": "Agentes autonomos com Go",
      "palestrante": "Tiago Temporim",
      "descricao": "Como desenvolver agentes autonomos de AI com Go e Gemini"
    }
  ]
}
```

### Speaker Spotlight

```json
{
  "titulo": "GDG Londrina Meetup Novembro 2025",
  "data": "29/11 (sabado)",
  "horario": "9h",
  "local": "Unicesumar Londrina",
  "link_inscricao": "https://www.sympla.com.br/...",
  "palestrante": {
    "nome": "Guilherme Bittencourt",
    "titulo_palestra": "Contabilidade, Impostos e Fiscalizacao dos CNPJ Tech",
    "descricao": "Organize sua vida financeira e fiscal para 2026",
    "bio": "Responsavel por empresas que movimentaram R$ 4 bilhoes em 2024",
    "credenciais": [
      "Socio da Fortmobile (Top 10 Startups PR - Sebrae 2024)",
      "Professor PUCPR ha 10 anos",
      "Gestor de +80 profissionais"
    ],
    "linkedin": "https://linkedin.com/in/guilhermebittencourt"
  }
}
```

### Newsletter Promo

```json
{
  "titulo": "Lideranca nao e sobre ser o mais inteligente",
  "subtitulo": "Como desenvolver sabedoria emocional e liderar projetos",
  "link": "https://gdglondrina.substack.com/p/...",
  "palestrante": "Nome do Palestrante",
  "insight_principal": "Os melhores lideres nao queriam ser lideres"
}
```

## CLI Usage

```bash
# Generate event announcement
python execution/generate_whatsapp.py --type event_announcement --input event_data.json

# Generate speaker spotlight (run once per speaker)
python execution/generate_whatsapp.py --type speaker_spotlight --input speaker_data.json

# Generate reminder
python execution/generate_whatsapp.py --type reminder --input event_data.json

# Generate newsletter promo
python execution/generate_whatsapp.py --type newsletter_promo --input newsletter_data.json

# Generate all pre-event messages at once
python execution/generate_whatsapp.py --type all_pre_event --input event_data.json
```

## Output Location

Messages are saved to `output/whatsapp/`:

```
output/whatsapp/
├── 2026-02-event_announcement.md
├── 2026-02-speaker_tiago-temporim.md
├── 2026-02-speaker_guilherme-bittencourt.md
├── 2026-02-reminder.md
└── 2026-02-newsletter_promo.md
```

## Integration with Newsletter Pipeline

### Pre-Event Flow

1. Create event in Sympla
2. Prepare `event_data.json` with event details
3. Generate event announcement: `--type event_announcement`
4. For each speaker, generate spotlight: `--type speaker_spotlight`
5. Day before, generate reminder: `--type reminder`

### Post-Event Flow

1. Run newsletter generation pipeline (video transcription -> summary -> newsletter)
2. Publish newsletter to Substack
3. Prepare `newsletter_data.json` with link and key insight
4. Generate newsletter promo: `--type newsletter_promo`

## Message Guidelines

### Platform Constraints
- Maximum ~200 words per message
- Emojis: strategic but not excessive
- Links: always include Sympla or Substack link
- Tone: conversational, community-focused, not corporate

### Key Patterns

**Event Announcement**: Hook with urgency/excitement, list date/time/location, list talks briefly, CTA with registration link

**Speaker Spotlight**: Hook based on the problem the talk solves, speaker credentials (3-4 bullet points), what they'll bring, CTA with registration link

**Reminder**: Short urgency hook, event details, quick talk list, scarcity message, CTA

**Newsletter Promo**: Provocative/curious hook, 1-2 sentences about the insight, promise of what they'll learn, CTA with newsletter link

## Related Files

- Prompts: `knowledge/prompts/whatsapp_*.md`
- Examples: `knowledge/examples/whatsapp-*.md`
- Execution: `execution/generate_whatsapp.py`

## Cost Estimation

Per message generation (2 alternatives):
- Input tokens: ~2,000-3,000
- Output tokens: ~500-800
- Estimated cost: ~$0.02-0.04

## Troubleshooting

### No output generated
- Check that input JSON file exists and is valid
- Verify API keys are configured in `.env`

### Message too long
- The prompts constrain to ~200 words, but if exceeded, manually trim

### Missing speaker data
- For speaker spotlight, ensure all required fields are in the JSON
- Bio and credentials are essential for building credibility
