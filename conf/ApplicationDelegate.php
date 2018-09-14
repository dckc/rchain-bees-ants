<?php
/**
 * A delegate class for the entire application to handle custom handling of
 * some functions such as permissions and preferences.
 */
class conf_ApplicationDelegate {
    /**
     * Returns permissions array.  This method is called every time an action is
     * performed to make sure that the user has permission to perform the action.
     * @param record A Dataface_Record object (may be null) against which we check
     *               permissions.
     * @see Dataface_PermissionsTool
     * @see Dataface_AuthenticationTool
     */
     function getPermissions(&$record){
         $auth =& Dataface_AuthenticationTool::getInstance();
         $user =& $auth->getLoggedInUser();

         $perms = Dataface_PermissionsTool::READ_ONLY();
         if ( !isset($user) ) return $perms;

         $role = $user->val('permission');

         // TODO: managers
         if ( $role == 'ADMIN' ) {
             $perms['clear views'] = 1;
         }

         $app =& Dataface_Application::getInstance();
         $query =& $app->getQuery();
         $action = $query['-action'];

         // OK to edit your own stuff
         if ( $record ) {
             $login = $user->val('login');
             if ( $login == $record->getValue('voter') and
                  ($action == 'view_related_record'  or
                   $action == 'view' or
                   $action == 'delete' or
                   $action == 'edit') ) {
                 $perms['edit'] = 1;
                 $perms['delete'] = 1;
                 $perms['delete related record'] = 1;
             }

             else if ($query['-table'] == 'github_users' and
                      $login == $record->getValue('login') and
                      ($action == 'related_records_list' or
                       $action == 'new_related_record') ) {
                 $perms['add new related record'] = 1;
             }
         }

         // Certify trusted users
         if ( isset($query['-relationship']) &&
              $query['-relationship'] == 'CertifiedBy') {
             $in_listing = $query['-action'] == 'related_records_list';
             $adding = $query['-action'] == 'new_related_record';

             // OK to add certification
             if ( $query['-table'] == 'github_users' ) {

                 if ( $in_listing or $adding ) {
                     $perms['add new related record'] = 1;
                 }
                 else if (isset($viewing) and $viewing and
                          $app->getRecord()->val('voter') == $user->val('login') ) {
                     $perms['edit'] = 1;
                     $perms['delete'] = 1;
                 }
             }

         }

         // Vote on budgets and rewards
         if ( isset($query['-relationship']) &&
              in_array($query['-relationship'],
                       array('BudgetVotes', 'RewardVotes')) ) {
             $in_listing = $query['-action'] == 'related_records_list';
             $adding = $query['-action'] == 'new_related_record';

             // OK to add vote to issue, budget, or reward
             if ( in_array($query['-table'], array('issue', 'issue_budget', 'reward')) ) {
                 // TODO: $perms['copy'] = 1;

                 if ( $in_listing or $adding ) {
                     $perms['add new related record'] = 1;
                 }
                 else if ($viewing and
                          $app->getRecord()->val('voter') == $user->val('login') ) {
                     $perms['edit'] = 1;
                     $perms['delete'] = 1;
                 }
             }

         }

         if ($query['-table'] == 'invoice_info') {
             // TODO: only your own!
             $perms = Dataface_PermissionsTool::getRolePermissions('DELETE');
         }
         return $perms;
     }

    public function beforeHandleRequest(){
        $app =& Dataface_Application::getInstance();
        $app->addHeadContent(
                sprintf('<link rel="stylesheet" type="text/css" href="%s"/>',
                        htmlspecialchars(DATAFACE_SITE_URL.'/templates/rchain-style.css')
                )
            );

        $query =& $app->getQuery();
        
        ###################
		#Here I check to see if they are coming from the Discord login. If they are, we need to check to see if they are a coop member.
		if(array_key_exists('discord_oauth_callback', $query) && $query['discord_oauth_callback'] == 'true')
		{
			$auth =& Dataface_AuthenticationTool::getInstance();
			$user =& $auth->getLoggedInUser();
			#make sure they are actually logged in
			if(isset($user))
			{
				$discordOauth = new discordOauthClass();
				#validate the user
				$discordUser = $discordOauth->checkIfUserValidCoopMember();  # or die trying
                    global $ini_array;
					#then save the validation flag to database
					$user->setValue($ini_array['verified_coop_column'], intval($discordUser->getId()));
                    $user->save(); 
			}
		}
    }

    function block__before_left_column() {
        $site = DATAFACE_SITE_HREF;
        $auth =& Dataface_AuthenticationTool::getInstance();
        $user =& $auth->getLoggedInUser();
        if (isset($user)) {
            $login = $user->val('login');
            echo <<<EOT
  <li><a href="{$site}?-table=github_users&amp;-action=related_records_list&amp;-mode=list&amp;-recordid=github_users%3Flogin%3D{$login}&-relationship=Reward">Rewards for {$login}</a></li>
EOT;
        }

        $current = substr(str_replace('-', '', current_pay_period()), 0, 6);
        echo "<ul><li>current: <b>$current</b></li>";
        echo <<<EOT
  <li><a href='https://github.com/rchain/bounties/wiki/How-To-Use-the-Budget-Rewards-Web-App'>Help / How-To</a>, <a href='https://github.com/rchain/bounties/wiki/VotingTrouble'>VotingTrouble</a></li>
  <ul>
    <li><a href='https://github.com/rchain/bounties/blob/master/CONTRIBUTING.md'>Bounty Process</a></li>
  </ul>
  <li><a href='aux/user'><b>Sync</b></li>
  <li><a href='trust_sync/trust_net_viz.html'>Trust Network</a></li>
</ul>
EOT;

    }
}


class HasPayPeriod {
    function pay_period__renderCell(&$record) {
        return fmt_pay_period($record->val('pay_period'));
    }
}

class VoteAuth extends HasPayPeriod {
     function voter__default() {
         $auth =& Dataface_AuthenticationTool::getInstance();
         $user =& $auth->getLoggedInUser();
         return $user->val('login');
     }

    function voter__permissions(&$record) {
        return ro_field();
    }
}

class PayPeriodVote extends VoteAuth {
    function pay_period__default () {
        return current_pay_period();
    }

    function pay_period__permissions(&$record) {
        return ro_field();
    }
}

function current_pay_period() {
    $res = df_query("select current_pay_period from admin_settings", null, true);
    if ( !$res ) throw new Exception(mysql_error(df_db()));
    $pp = $res[0]['current_pay_period'];
    return $pp;
}

function fmt_pay_period($pp) {
    $yyyymm = sprintf('%04d%02d', $pp['year'], $pp['month']);
    return $yyyymm;
}


function ro_field() {
    # http://xataface.com/forum/viewtopic.php?t=5657#27106
    $perms = Dataface_PermissionsTool::NO_ACCESS();
    $perms['view']=1;
    $perms['list']=1;
    return $perms;
}

function link_markup($href, $content) {
		return '<a href="'.htmlspecialchars($href).'" >'.$content.'</a>';
}

?>
