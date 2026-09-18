const listStartups = require('./netlify/functions/list-startups').handler;

async function run() {
    const res = await listStartups({ queryStringParameters: { judge_id: 'J-001', passcode: 'demo2025' } });
    console.log(res);
}
run();
