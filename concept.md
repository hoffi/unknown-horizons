## Concept Scenarios

### Directory Structure

+ scenarios/
  + [scenario-name]/
     + images/
     + translations/
     + package-info.yaml
     + [name].yaml

### package-info.yaml

> Work in progress...

```yaml
name: "[scenario-name]"
difficulty: "[easy|medium|hard]"
author: "[your-name]"
author-email: "[your-email]"
created: "[dd-mm-yyyy]"
short-description: "[...]"
description: "[...]"
```

### [name].yaml

> Work in progress...

```yaml
intro:
 text-key: "KEY_OF_TRANSLATION"
 delayed: [0..x]
 
main:
 -
  type: [task|story]
  text-key: "KEY_OF_TRANSLATION"
  preconditions:
   -
    type: [start|resource|...]
    condition: [lt|gt|eq]
    item: [? eg. "gold"]
    value: [? eg "100"]
  actions:
   -
    type: [message|resource]
    ...
```
