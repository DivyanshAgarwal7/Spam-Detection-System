// backend/utils/despamificationRules.js

const replacements = {
  'URGENT': 'Someone wants to contact you',
  'FREE': 'There is an offer',
  'WIN': 'There is a notification',
  'PRIZE': 'There is a message about rewards',
  'CLAIM': 'There is a message for you',
  'CLICK': 'There is a link to visit',
  'NOW': 'soon',
  '!!!': '.',
  '$$$': '',
  '100%': '',
  'GUARANTEED': '',
  'LIMITED TIME': '',
  'ACT NOW': '',
  "DON'T MISS": '',
  'EXCLUSIVE': '',
  'YOU WON': 'There is a notification'
};

const tonePrefixes = {
  neutral: '',
  friendly: 'Hi there! ',
  formal: 'We would like to inform you that ',
  casual: 'Hey! '
};

module.exports = { replacements, tonePrefixes };