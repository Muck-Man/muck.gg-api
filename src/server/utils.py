from enum import Enum

class Enumerable(Enum):

	@classmethod
	def get(cls, key, default=None):
		try:
			return cls[key]
		except:
			return default
	
	@classmethod
	def get_value(cls, value, default=None):
		try:
			return cls(value)
		except:
			return default

	def __str__(self):
		return self.name

class Permissions(Enumerable):
	OWNER            = 1 << 1
	SUPERADMIN       = 1 << 2
	ADMIN            = 1 << 3

	@classmethod
	def check(cls, permission, check):
		if not isinstance(check, cls):
			check = cls.get(check)
		return check is not None and ((permission & check.value) == check.value)
	
	@classmethod
	def check_any(cls, permission, checks):
		return any(cls.check(permission, check) for check in checks)

class ContextTypes(Enumerable):
	GLOBAL = 0
	GUILDS = 1
	CHANNELS = 2

class PerspectiveAttributes(Enumerable):
	ATTACK_ON_AUTHOR    = 'attack_on_author'
	ATTACK_ON_COMMENTER = 'attack_on_commenter'
	INCOHERENT          = 'incoherent'
	INFLAMMATORY        = 'inflammatory'
	LIKELY_TO_REJECT    = 'likely_to_reject'
	OBSCENE             = 'obscene'
	SEVERE_TOXICITY     = 'severe_toxicity'
	SPAM                = 'spam'
	TOXICITY            = 'toxicity'
	UNSUBSTANTIAL       = 'unsubstantial'
