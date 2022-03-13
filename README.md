#LWxposter

Code that cross-posts from LessWrong community posts such as those [found here](https://www.lesswrong.com/upcomingEvents).

To be deployed as an AWS Lambda function that pulls new posts from the LessWrong API on a fixed schedule.

Includes the ability to crosspost to email, Facebook (in development), and Discord.

The target addresses are not public, but an example of the input format is included as destinations_format.json.
