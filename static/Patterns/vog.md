# Super Gene Regular Expressions

## Voice of God

### Killed
```python
r"^(?P<vog_killed>\"(?P<creature>[ \w-]+) killed\.?.*beast soul.*eat.*point.*\")$|^(?P<vog_killed_trunc>\"(?P<creature_trunck>[ \w-]*) killed.*\")$"
```

### Killed Truncated
```python
r"^(?P<vog_killed>\"(?P<creature>[ \w-]+) killed\.?.*beast soul.*eat.*point.*\")$
```

#### Killed Truncated
```python
r"^(?P<vog_killed_trunc>\"(?P<creature_trunck>[ \w-]*) killed.*\")$"
```


