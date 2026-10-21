import {money,escapeHtml as e,Api,showError,clearError,busy,toast,validateForm,confirmAction} from './api-client.js';
import {initShell} from './shell.js';
import {shopIdentity,planState} from './shop-view.js';
const $=id=>document.getElementById(id),isAdmin=document.body.dataset.role==='ADMIN';
let selectedShop=null,saving=false;
async function load(){
  clearError($('planError'));selectedShop=null;if($('assignFields'))$('assignFields').disabled=true;
  const shop=document.body.dataset.shop;
  try{
    const [result,detail]=await Promise.all([Api.request(Api.scoped('/api/subscription')),isAdmin?Api.request('/api/admin/shops/'+shop):Promise.resolve(null)]);
    const labels={categories:'Danh mục',products:'Sản phẩm',accounts:'Tài khoản',branches:'Chi nhánh',attendance:'Nhân viên chấm công'};
    $('usageGrid').innerHTML=Object.entries(result.data.usage).map(([key,used])=>'<div class="col-sm-6 col-lg"><div class="stat-tile"><span>'+labels[key]+'</span><strong>'+used+' / '+(result.data.limits[key]??'∞')+'</strong></div></div>').join('');
    $('quotaWarning').textContent=result.data.over_limit.length?'Dữ liệu đang vượt hạn mức: '+result.data.over_limit.map(key=>labels[key]).join(', ')+'. Lịch sử được giữ lại; không thể tạo hoặc kích hoạt thêm cho tới khi giảm mức sử dụng hoặc nâng gói.':'';
    $('currentPlan').textContent=result.data.effective_plan==='PRO'?'Pro':'Standard';
    $('planDates').textContent=result.data.fallback?((planState[result.data.status]||'Gói mặc định')+'; cửa hàng đang dùng Standard.'):`Hiệu lực từ ${result.data.start_date} đến ${result.data.end_date||'không giới hạn'} (UTC)`;
    if(isAdmin){selectedShop=detail.data;$('shopIdentity').innerHTML=shopIdentity(selectedShop);$('assignPlan').value=result.data.effective_plan;$('planEndDate').value=result.data.fallback?'':(result.data.end_date||'');$('assignFields').disabled=false;}
  }catch(error){$('usageGrid').replaceChildren();$('quotaWarning').textContent='';$('currentPlan').textContent='Chưa xác định';$('planDates').textContent='';if($('shopIdentity'))$('shopIdentity').textContent='Chọn một cửa hàng hợp lệ để xem tài khoản và cấp gói.';throw error;}
}
$('assignPlanForm')?.addEventListener('submit',async event=>{
  event.preventDefault();const form=event.currentTarget;if(saving||!selectedShop||!validateForm(form))return;
  const shop=selectedShop,plan=$('assignPlan').value,end=$('planEndDate').value||null;
  saving=true;
  try{
    if(!await confirmAction(`Cấp gói ${plan} cho cửa hàng ID ${shop.shop_id} — ${shop.shop_name} (chủ shop: ${shop.owner?.username||'chưa có'})?`,'Cấp gói'))return;
    const button=form.querySelector('[type="submit"]');busy(button,true);clearError($('planError'));
    try{const result=await Api.request('/api/admin/shops/'+shop.shop_id+'/subscription',{method:'POST',body:{plan,end_date:end}});toast(result.message);await load();}
    finally{busy(button,false);}
  }catch(error){showError($('planError'),error);}finally{saving=false;}
});
async function main(){await initShell();const catalog=(await Api.request('/api/subscription/plans')).data;const pro=catalog.find(row=>row.plan==='PRO');$('proPrice').textContent=money(pro.price);$('billingCycle').textContent=pro.billing_cycle?'Chu kỳ thu phí: '+pro.billing_cycle:'Chu kỳ thu phí chưa được quy định';await load();}
main().catch(error=>showError($('planError'),error));
