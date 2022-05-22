# Refold Archive Bot

A Discord Bot to assist with archiving messages.

Many additional features will be coming "soon&trade;".

## How to Setup

### Create a Discord Bot and Get its OAuth2 Token

In order for this app to run it needs two things:

1. A bot account created in Discord.
2. An OAuth2 token for this script to sign in to the bot account.

Please review this guide for details on how to do both here:<br>
[Discord.js Bot Setup Guide](https://discordjs.guide/preparations/setting-up-a-bot-application.html#creating-your-bot)

### Setup Environment

This application is written using Node.js (v14 LTS).

Please follow this guide to install Node.js for your operating system:<br>
[Node.js Installation Guide](https://nodejs.org/en/download/package-manager/)

After Node.js is installed, confirm you are using at least
version 14 using this command:

```sh
node --version
```

### Install Dependencies

This application is built on top of:

- [Discord.js Library](https://discord.js.org/)

- [fs](https://nodejs.dev/learn/the-nodejs-fs-module)

In order to use these libraries you must either install them from the
package.json file or manually from npm.

A. Install from package.json:

```sh
cd <project-directory>
npm install
```

B. Install manually from npm:

```sh
npm install --save discord.js sequelize fs
```

### Set Config File Values

#### Config.json

The `config.json` file holds most values you will need to set.

The most important value to edit is the `token` value, which is how the bot
authenticates on your Discord Server. This should be set to the token value
acquired earlier from Discord.

The `prefix` value is a special character that must be placed immediately
before a command. This can be set to anything you want, or even made blank.

The `emojis` is a list of **all** emojis that the bot will watch reactions for.

Note: The commands themselves will each have a list of emojis to respond to, but if
the command's emoji isn't on this list, it will not trigger.

#### Commands

The `commands` directory contains each command.

Each command can be activated by either:

1. The user typing a command or its aliases with a prefix in their post.
2. Any user can react to a post with predetermined emojis.

Each command features a "cool down", which requires that a user wait a certain
number of seconds before using a command again. This prevents users from
flooding the bot with requests.

Feel free to change these commands by doing any of the following:

- Rename the command file (it's filename acts as the main command name).
- Edit the `aliases` list to whatever is preferable.
- Edit the `emojis` list to whatever is preferable.
- Edit the `cooldown` value to the number of seconds a user must wait before
  being able to use the command again.

You can also add your own commands into this directory to have them picked up
when the bot is restarted.

### Run Application for Testing/Develpoment

The application needs the OAuth2 token to be specified within
the `config.json` file or defined on the commandline.

A. Edit the `config.json` file and set the `token` value:

```json
"token": "<OAuth2_token_goes_here>"
```

Then run the app with node:

```sh
node index.js
```

B. Define your bot's token value on the command line and
run it at the same time:

```sh
token='<OAuth2_token_goes_here>' node index.js
```

### Run Application in Production

I highly recommend running this app using a process manager like PM2.

For instructions on how to install and use PM2, please see this guide:
[PM2](https://pm2.keymetrics.io/)

After PM2 is installed, edit the `config.json` file and set the `token` value:

```json
"token": "<OAuth2_token_goes_here>"
```

Then start the app with PM2:

```sh
cd <directory-above-project>
pm2 start <project-directory>
```

Alternatively, start the app with PM2 inside the project directory:

```sh
cd <project-directory>
pm2 start index.js
```

Monitoring of the app can be done with:

```sh
pm2 monit
```

## How to Use

Each of these commands will include information on how to use them based on
their default configuration.

### Archive

Archive will make a copy of a user's post and any URLs it contains and then
post an embed of the original post and separate posts for each URL (so that
they each get an auto-generated embed).

The `config.json` file contains a list of channels to archive `from` and `to`.<br>
The command only works on the channels that match the `from` values
(the default is `#general` to `#archive`).

Note: The `from` and `to` values are case-sensitive.

Trigger:

> !archive

Aliases:

> !share !save

Emojis:

> 📎 💾 📌

## LICENSE

Licensed under GNU GPLv3.

See [LICENSE](LICENSE) file for further details.
