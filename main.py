# literals: abc1234
# metacharacters: *+.?
# Grammar:
# literal -> ('a' | '1' | '.') | '(' exp ')''
# postfix -> literal '*+?'*
# many -> postfix+
# or -> postfix ('|' postfix)*
# exp -> or

# The algorithm:
# for a literal just add the character to the fragment on top of the stack
# for metacharacter, pop from the stack and modify

from typing import Callable, Optional

META_CHARACTERS = ['*', '+', '.', '?', '|', '(', ')', '\\']


class State:
  out: Optional['State']
  out1: Optional['State']
  char: Optional[str]
  traversal_id = -1

  def __init__(self, char=None, out=None, out1=None):
    self.char = char
    self.out = out
    self.out1 = out1

  def __str__(self) -> str:
    if self.is_split():
      return "SPLIT"
    if self.is_match():
      return "MATCH"
    if self.is_wild():
      return "ANY"
    return self.char or ""

  def set_out(self, state):
    self.out = state

  def set_out1(self, state):
    self.out1 = state

  def is_split(self):
    return self.out and self.out1

  def is_match(self):
    return self.char == "MATCH"

  def is_wild(self):
    return self.char == "ANY"


class Fragment:
  start: State
  dangling: list[Callable[[State], None]]

  def __init__(self, start: Optional[State] = None):
    if start:
      self.start = start
      self.dangling = [start.set_out]

  def fill_dangling(self, state: State):
    for set in self.dangling:
      set(state)


class Regex:
  i = 0
  traversal_id = -1

  def __init__(self, regex: str):
    self.regex = regex
    self.init_state = self.parse()

  def isEof(self):
    return self.i == len(self.regex)

  def check(self, chars: list[str]) -> bool:
    return self.check_cond(lambda c: c in chars)

  def check_cond(self, cond) -> bool:
    if self.isEof():
      return False
    return cond(self.regex[self.i])

  def next(self):
    self.i = self.i + 1

  def curr(self):
    return self.regex[self.i]

  def parse_escaped(self):
    if self.check(['\\']):
      self.next()
      if self.check(META_CHARACTERS):
        curr = self.curr()
        self.next()
        return curr
      return '\\'
    return None

  def parse_literal(self) -> Optional[Fragment]:
    if self.check_cond(lambda c: c not in META_CHARACTERS):
      if c := self.parse_escaped():
        return Fragment(State(char=c))
      else:
        c = self.curr()
        self.next()
        return Fragment(State(char="ANY" if c == '.' else c))
    if self.check(['(']):
      self.next()
      frag = self.parse_or()
      if not self.check([')']):
        raise Exception("Unmatched parenthesis")
      self.next()
      return frag
    return None

  def parse_postfix(self) -> Optional[Fragment]:
    frag = self.parse_literal()
    if frag is None:
      return None
    while True:
      if (self.check(['*'])):
        state = State()
        state.out = frag.start
        frag.fill_dangling(state)
        frag.dangling = [state.set_out1]
        frag.start = state
      elif (self.check(['+'])):
        state = State()
        state.out = frag.start
        frag.fill_dangling(state)
        frag.dangling = [state.set_out1]
      elif self.check(['?']):
        state = State()
        state.out = frag.start
        frag.start = state
        frag.dangling.append(state.set_out1)
      else:
        break
      self.next()
    return frag

  def parse_many(self) -> Optional[Fragment]:
    frag = self.parse_postfix()
    if frag is None:
      return None
    while True:
      next = self.parse_postfix()
      if next is None:
        break
      frag.fill_dangling(next.start)
      frag.dangling = next.dangling
    return frag

  def parse_or(self) -> Fragment:
    frag = self.parse_many()
    if frag is None:
      raise
    while self.check(["|"]):
      self.next()
      frag2 = self.parse_many()
      if frag2 is None:
        raise
      state = State()
      state.out = frag.start
      state.out1 = frag2.start
      frag.start = state
      frag.dangling = frag.dangling + frag2.dangling
    return frag

  def parse(self) -> State:
    frag = self.parse_or()
    frag.fill_dangling(State(char="MATCH"))
    return frag.start

  def match(self, input: str) -> bool:
    states = []
    self.traversal_id += 1
    self.add_state(self.init_state, states)
    for c in input:
      self.traversal_id += 1
      next_states: list[State] = []
      for state in states:
        if state.char == "ANY" or state.char == c:
          self.add_state(state.out, next_states)
      states = next_states
    return any(state.is_match() for state in states)

  def add_state(self, state: Optional[State], states: list[State]):
    if state is None or state.traversal_id == self.traversal_id:
      return
    state.traversal_id = self.traversal_id
    if state.is_split():
      self.add_state(state.out, states)
      self.add_state(state.out1, states)
    else:
      states.append(state)
