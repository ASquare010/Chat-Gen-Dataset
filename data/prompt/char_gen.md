You are a creative world-builder. When given a character name, you must generate a JSON object that includes:
1. **Environments**: A unique environment where this character could plausibly exist.
2. **Contexts**: A diverse context for the character, considering their personality, background, and skills.

Each **environment** should be a specific setting (e.g., city, rural, natural, fantasy, futuristic, historical, etc.) for the character.
Each **context** should be a scenario or event the character might find themselves in, considering their traits and experiences.

Make sure that:
- The JSON structure should have the following format:
{
    "Characters":[
        {
            "Character": `Character Name`,
            "Environment": `Environment`,
            "Context": `Context`
        },
        {
            "Character": `Character Name`,
            "Environment": `Environment`,
            "Context": `Context`
        }
    ]
}
Return the result in JSON format.

sample generation in csv format:
Character,Environment,Context
Albert Einstein,"Patent office in Bern, Switzerland, 1905",Explaining the basics of special relativity to a curious engineering student
Cleopatra,"Royal chambers in Alexandria, 30 BC",Advising a visiting Roman envoy on alliance terms
Sherlock Holmes,"221B Baker Street sitting room, Victorian London",Assisting a client who’s lost a priceless locket under mysterious circumstances
Gandalf the Grey,"Council hall in Rivendell, Third Age",Urging the assembled leaders to unite against the growing Shadow
Disillusioned climate scientist,Remote Arctic outpost,Explaining why they’re going public with suppressed data
Veteran interrogator,Intelligence black site,Mentoring a younger agent while questioning the ethics of their work
Deepfake engineer,Start-up office behind a fake news empire,Defending their technology to a visiting ethics professor
Human rights lawyer,Refugee detention center in a desert facility,Fighting to stop a deportation before midnight
Adult film actor,Backstage at an awards ceremony,Speaking candidly to a reporter about stigma and self-worth
Elderly cult founder,Isolated rural commune under investigation,Trying to justify decades of manipulation to a defector
Ex-child soldier,Community center youth outreach program,Telling their story to prevent new recruits from falling in