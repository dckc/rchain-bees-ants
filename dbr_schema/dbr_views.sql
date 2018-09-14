create or replace view user_flair as
select u.login, u.verified_coop, r.rating
     , elt(field(r.rating, 1, 2, 3), 'apprentice', 'journeyer',  'master') rating_label
     , elt(field(r.rating, 1, 2, 3), 1, 3,  7) weight
     , concat(u.login,
              case when u.verified_coop is null then '?'
	           else ':' end,
              coalesce(elt(field(r.rating, 1, 2, 3), 'a*1', 'j*3',  'm*7'), '')) sig
from github_users u  -- ISSUE: skip github_users and let caller deal with missing flair?
left join authorities r on u.login = r.login
;


create or replace view issue_budget_unwt as
select issue_num, title
    , case when voter_qty >= 3 then budget_provisional else null end budget_usd
    , budget_provisional, voter_qty, voters, pay_period, labels
from (
	select bv.issue_num, i.title, i.labels
	     , count(distinct uf.verified_coop) voter_qty
	     , group_concat(uf.sig separator ', ') voters
	     , round(avg(bv.amount), 2) budget_provisional
             , bv.pay_period
	from issue i
	    join budget_vote bv on bv.issue_num = i.num
	    join user_flair uf on uf.login = bv.voter and uf.verified_coop is not null
	    join pay_period pp on pp.start_date = bv.pay_period and pp.weighted=0 
	group by bv.pay_period, i.num, i.title
) ea
;
-- select * from issue_budget;

create or replace view issue_budget_wt as
select issue_num, title
    , case when voter_qty >= 3 then budget_provisional else null end budget_usd
    , budget_provisional, voter_qty, voters, pay_period, labels
from (
	select bv.issue_num, i.title, i.labels
	     , count(distinct verified_coop) voter_qty
	     , group_concat(sig separator ', ') voters
	     , round(sum(bv.amount * weight) / sum(weight), 2) budget_provisional
             , bv.pay_period
	from issue i
 	join (
	  select coalesce(bv.weight, uf.weight) weight
	       , concat(bv.voter, '*', coalesce(bv.weight, uf.weight)) sig
	       , uf.verified_coop
	       , bv.issue_num, bv.pay_period, bv.amount
	  from budget_vote bv
	  join user_flair uf on uf.login = bv.voter
          where uf.verified_coop is not null
	) bv on bv.issue_num = i.num
        join pay_period pp on pp.start_date = bv.pay_period and pp.weighted=1
	group by bv.pay_period, i.num, i.title
) ea
;

create or replace view issue_budget as
select * from issue_budget_unwt
union all
select * from issue_budget_wt;

create or replace view reward_unwt as
select issue_num, title
     , worker
     , case when voter_qty >= 3 then reward_usd_1 else null end reward_usd
     , percent_avg
     , budget_usd
     , voter_qty, voters
     , reward_provisional
     , budget_provisional
     , pay_period, labels
from (
	select ib.pay_period, ib.issue_num, ib.title, ib.labels, rv.worker
	     , count(distinct uf.verified_coop) voter_qty
	     , group_concat(uf.sig separator ', ') voters
             , ib.budget_provisional
             , ib.budget_usd
	     , round(avg(rv.percent), 2) percent_avg
	     , round(avg(rv.percent) / 100 * ib.budget_provisional) reward_provisional
	     , round(avg(rv.percent) / 100 * ib.budget_usd) reward_usd_1
	from issue_budget_unwt ib
	join reward_vote rv on rv.issue_num = ib.issue_num and rv.pay_period = ib.pay_period
        join user_flair uf on uf.login = rv.voter and uf.verified_coop is not null
	group by ib.pay_period, ib.issue_num, ib.title, rv.worker
) ea
;

create or replace view slash_judgement as
select worker, group_concat(uf.sig separator ', ') voters, sum(uf.weight) weight
     , issue_num
     , pay_period
from reward_vote rv
join user_flair uf on uf.login = rv.voter
where slash > 0
group by rv.worker, issue_num, pay_period
having sum(uf.weight) >= 10
;

create or replace view reward_wt as
select issue_num, title
     , worker
     , case
       when exists (
        select 1
	from slash_judgement sj
        where sj.pay_period = ea.pay_period
        and sj.worker = ea.worker
	) then 0
       when voter_qty >= 3 then reward_usd_1
       else null
       end reward_usd
     , percent_avg
     , budget_usd
     , voter_qty, voters
     , reward_provisional
     , budget_provisional
     , pay_period, labels
from (
	select ib.pay_period, ib.issue_num, ib.title, ib.labels, rv.worker
	     , count(distinct verified_coop) voter_qty
	     , group_concat(sig separator ', ') voters
             , ib.budget_provisional
             , ib.budget_usd
	     , round(sum(rv.percent * weight) / sum(weight), 2) percent_avg
	     , round(sum(rv.percent * weight) / sum(weight) / 100 * ib.budget_provisional) reward_provisional
	     , round(sum(rv.percent * weight) / sum(weight) / 100 * ib.budget_usd) reward_usd_1
	from issue_budget_wt ib
	join (
	  select coalesce(rv.weight, uf.weight) weight
	       , concat(rv.voter, '*', coalesce(rv.weight, uf.weight)) sig
	       , uf.verified_coop
	       , rv.issue_num, rv.pay_period, rv.percent, rv.worker
	  from reward_vote rv
	  join user_flair uf on uf.login = rv.voter
          where uf.verified_coop is not null
	) rv on rv.issue_num = ib.issue_num and rv.pay_period = ib.pay_period
	group by ib.pay_period, ib.issue_num, ib.title, rv.worker
) ea
;
-- eyeball it: select * from reward_wt order by voter_qty desc;
create or replace view reward as
select * from reward_fixed
union all select * from (
  select * from reward_unwt
  union all
  select * from reward_wt
) dyn where dyn.pay_period >= (select current_pay_period from admin_settings);

create or replace view task_approval_overdue as
select i.* from (
  select num issue_num, title, state
       , datediff(current_timestamp, i.createdAt) days_old
       , round(datediff(current_timestamp, i.createdAt) / 7 ) weeks_old
       , labels, createdAt, updatedAt
  from issue i
  where i.updatedAt < date_sub(current_timestamp, interval 36 hour) -- issues discussed recently are excused
  and ((i.state = 'OPEN' and i.labels not like '%"needs-SMART-objective"%')
       or 
       (i.state = 'CLOSED'
        and datediff(current_timestamp, i.updatedAt) < 60  -- updated in the last pay period or two
	and i.labels not like '%"needs-SMART-objective"%'
        and i.labels not like '%"invalid"%'
        and i.labels not like '%"wontfix"%'
	and i.labels not like '%"duplicate"%'))
) i
left join issue_budget ib on ib.issue_num = i.issue_num
where days_old between 5 and 90
and ib.issue_num is null  -- no budget votes at all, let alone a critical mass
order by days_old desc
;

create or replace view invoice_summary as
  select pay_period, worker
, group_concat(issue_num separator ', ') as issues
, sum(reward_usd) USD
, sum(reward_usd) / rate RHOC
from reward r
join pay_period pp on pp.start_date = r.pay_period
where r.reward_usd > 0
group by r.pay_period, r.worker;
