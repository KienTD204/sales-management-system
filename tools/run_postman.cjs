/* Chạy trên CSDL demo riêng đã nhập database_schema.sql. */
const newman=require('newman');
const fs=require('node:fs');
const path=require('node:path');
const root=path.resolve(__dirname,'..');
const baseURL=process.env.E2E_BASE_URL||'http://127.0.0.1:5000';
async function run(name,file,environment,delayRequest=0){
 return new Promise((resolve,reject)=>{
  newman.run({collection:require(path.join(root,'postman',file)),environment:environment?require(path.join(root,'postman',environment)):{values:[]},envVar:[{key:'base_url',value:baseURL}],delayRequest,reporters:[]},(error,summary)=>{
   const result={executed_at:new Date().toISOString(),runner:'Newman 6.2.2',base_url:baseURL,requests:summary?.run.stats.requests,assertions:summary?.run.stats.assertions,failures:summary?.run.failures.map(row=>({source:row.source.name,message:row.error.message})),error:error?.message};
   fs.mkdirSync(path.join(root,'docs/test-results'),{recursive:true});fs.writeFileSync(path.join(root,`docs/test-results/newman-${name}.json`),JSON.stringify(result,null,2));console.log(name,JSON.stringify(result));
   if(error||result.failures?.length)reject(error||new Error(name+' failed'));else resolve();
  });
 });
}
(async()=>{await run('week678','Week678.postman_collection.json','Week678.postman_environment.json');await run('workspaces','Workspaces.postman_collection.json');await run('plans','PlansWorkforce.postman_collection.json',null,1000);})().catch(error=>{console.error(error.message);process.exitCode=1;});
