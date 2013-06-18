## Scenarios Ideas

### Directory Structure

+ scenarios/
  + [scenario-name]/
     + images/
     + translations/
     + package-info.yaml
     + [name].yaml

### package-info.yaml

> Contains all informations about this Scenario

```yaml
name: "[scenario-name]"
difficulty: "[easy|medium|hard]"
author: "[your-name]"
author-email: "[your-email]"
created: "[dd-mm-yyyy]"
short-description: "[...]"
description: "[...]"
map-file: "..."
```

### [name].yaml

> Contains all events for this scenario

```yaml
intro:
 text-key: "KEY_OF_TRANSLATION"
 delayed: [0..x]
 
events:
 - type: [task|story]
   text-key: "KEY_OF_TRANSLATION"
   preconditions:
    - type: [lt|gt|eq|...]
      item: ["gold", 100]
   actions:
    - type: [message|resource]
      arguments: ["This is a message"|"gold", +100|"gold", -100]

win:
 text-key: "KEY_OF_WIN_MESSAGE_TRANSLATION"
 - condition:
  - type: [lt|gt|eq|...]
    item: ["gold", 200]
```

### images/

> Contains all images for this Scenario that should be shown in the logbook

### translations/

> Contains all translations for this Scenario that should be shown in the logbook

> Maybe use something like 'Markdown' for Text-Formatting?

> '#' for Headlines, '!(DESCRIPTION)[PATH]' for images, '---' for hr.png

> Use the keys defined in the [name].yaml

### Scenario Editor

> TBD (Maybe as webapp?)


## Campaigns

### Directory Structure

+ scenarios/
  + [campaign-name]/
     + shared_images/
     + shared_translations/
     + package-info.yaml
     + [scenario1_name]/
     + [scenario2_name]/
     + [...]/

### shared_images/

> Contains all images that will be shared and are available in all scenarios of this Campaign

### shared_translations/

> Same as images just for translations

### package-info.yaml

> Contains basic infos of this campaign

### [scenarioX_name]/

> A scenario of this campaign (see above for its directory structure)

