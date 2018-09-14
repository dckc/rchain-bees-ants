delimiter //
drop trigger if exists percent_max_100_insert //
create trigger percent_max_100_insert
before insert on reward_vote for each row
begin
  declare pct_tot int;
  select coalesce(sum(greatest(percent, 0)), 0) into pct_tot
  from reward_vote cur
  where cur.pay_period = new.pay_period
    and cur.issue_num = new.issue_num
    and cur.voter = new.voter;
  if(pct_tot + new.percent > 100) then
    signal sqlstate '45000' set message_text = 'Your reward votes on this issue would exceed 100%.';
  end if;
end
//

drop trigger if exists percent_max_100_update //
create trigger percent_max_100_update
before update on reward_vote
for each row
begin
  declare pct_tot int;
  select coalesce(sum(greatest(percent, 0)), 0) into pct_tot
  from reward_vote cur
  where cur.pay_period = new.pay_period
      and cur.issue_num = new.issue_num
      and cur.voter = new.voter;
  if(pct_tot - old.percent + new.percent > 100) then
      SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Your reward votes on this issue would exceed 100%.';
  end if;
end
//

create procedure ensure_vote_current(issue_num int, pay_period date)
begin
  declare current_start date;
  declare current_end date;
  declare issue_created date;
  select current_pay_period, pp.end_date into current_start, current_end
  from admin_settings admin
  join pay_period pp on admin.current_pay_period = pp.start_date;
  select createdAt into issue_created
  from issue where issue.num = issue_num;

  if (pay_period != current_start) then
    signal sqlstate '45000' set message_text = 'votes must use current pay period';
  end if;
  if (issue_created > current_end) then
    signal sqlstate '45000' set message_text = 'No votes on issues created after the current pay period';
  end if;
end
//

create trigger current_edit_bv_insert
before insert on budget_vote for each row begin
  call ensure_vote_current(new.issue_num, new.pay_period);
end
//
create trigger current_edit_rv_insert
before insert on reward_vote for each row begin
  call ensure_vote_current(new.issue_num, new.pay_period);
end
//
create trigger current_edit_bv_delete
before delete on budget_vote for each row begin
  call ensure_vote_current(old.issue_num, old.pay_period);
end
//
create trigger current_edit_rv_delete
before delete on reward_vote for each row begin
  call ensure_vote_current(old.issue_num, old.pay_period);
end
//
drop trigger current_edit_bv_update;
create trigger current_edit_bv_update
before update on budget_vote for each row begin
  call ensure_vote_current(old.issue_num, old.pay_period);
  if (new.pay_period != old.pay_period) then
    signal sqlstate '45000' set message_text = 'cannot change pay period';
  end if;
end
//
drop trigger current_edit_rv_update;
create trigger current_edit_rv_update
before update on reward_vote for each row begin
  call ensure_vote_current(old.issue_num, old.pay_period);
  if (new.pay_period != old.pay_period) then
    signal sqlstate '45000' set message_text = 'cannot change pay period';
  end if;
end
//
