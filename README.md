#LWxposter

Code that cross-posts from LessWrong community posts such as those [found here](https://www.lesswrong.com/upcomingEvents).

Intended to be deployed as an AWS Lambda function is scheduled to pull new posts from the LessWrong API.

Includes the ability to crosspost to email, Facebook (in development), and Discord.

The targets and their API keys are not public, but an example is included in destinations_format.json.