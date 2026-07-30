/* Native launcher for Local Dictation.app.
 *
 * TCC (Accessibility/Microphone) grants are validated against the code
 * identity of the app's main process. A shell-script executable runs as
 * /bin/zsh — an Apple binary that can never match the bundle's signature,
 * so grants silently fail and macOS re-prompts forever. This binary is
 * compiled into the bundle and signed with it, then keeps running as the
 * bundle's main process while Python does the work as its child (child
 * permission checks attribute to this "responsible process").
 *
 * The child's path is passed at compile time via -DCHILD_PATH.
 */

#include <signal.h>
#include <spawn.h>
#include <stdio.h>
#include <stdlib.h>
#include <sys/wait.h>
#include <unistd.h>

extern char **environ;

static pid_t child_pid = 0;

static void forward_signal(int sig) {
    if (child_pid > 0) {
        kill(child_pid, sig);
    }
}

int main(void) {
    char *argv[] = {CHILD_PATH, NULL};
    if (posix_spawn(&child_pid, CHILD_PATH, NULL, NULL, argv, environ) != 0) {
        perror("posix_spawn");
        return 127;
    }

    signal(SIGTERM, forward_signal);
    signal(SIGINT, forward_signal);
    signal(SIGHUP, forward_signal);

    int status = 0;
    while (waitpid(child_pid, &status, 0) < 0) {
        /* interrupted by a forwarded signal — keep waiting */
    }
    return WIFEXITED(status) ? WEXITSTATUS(status) : 128 + WTERMSIG(status);
}
