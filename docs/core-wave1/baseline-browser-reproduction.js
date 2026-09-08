import {test,expect} from '@playwright/test';
async function login(page) {
 await page.goto('/login');
 await page.getByLabel('Username').fill('wave1-learner');
 await page.getByLabel('Password').fill(process.env.WAVE1_PASSWORD);
 await page.getByRole('button',{name:'Login',exact:true}).click();
 await expect(page).toHaveURL(/\/$/);
}
async function submit(page,id,pass) {
 const data=(await (await page.request.get(`http://127.0.0.1:8029/api/quizzes/${id}`)).json()).data;
 const result=await page.request.post(`http://127.0.0.1:8029/api/quizzes/${id}/submit`,{headers:{Origin:'http://127.0.0.1:5189'},data:{student_id:1,answers:Object.fromEntries(data.questions.map(q=>[String(q.id),pass?'A':'B']))}});
 expect(result.status()).toBe(200);
}
test('baseline Today must report 4/4 as 100%',async({page})=>{
 await login(page); await submit(page,1,true); await page.goto('/');
 await expect(page.getByText('Score 4%',{exact:true})).toBeVisible();
 await page.screenshot({path:'/tmp/core-wave1-before-verified/today-4-percent.png',fullPage:true});
 await expect(page.getByText('Score 100%',{exact:true})).toBeVisible();
});
test('baseline saved review must select the latest passing attempt',async({page})=>{
 await login(page); await submit(page,2,false); await submit(page,2,true);
 await page.goto('/quizzes/2/review');
 await expect(page.getByText('0%',{exact:true}).first()).toBeVisible();
 await page.screenshot({path:'/tmp/core-wave1-before-verified/review-earlier-failure.png',fullPage:true});
 await expect(page.getByText('100%',{exact:true}).first()).toBeVisible();
});
