package org.example.hclcapstonebe.Utilities;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.example.hclcapstonebe.Repository.UserRepository;
import org.springframework.boot.CommandLineRunner;
import org.springframework.stereotype.Component;

/**
 * Issue #224 -- SampleDataRunner's standalone main() left the running dev
 * DB's seed state untracked and unreproducible (manager logins that
 * "should" exist per source didn't actually work, since nobody had rerun
 * it recently). Seeds automatically on every BE startup, but ONLY if the
 * users table is empty -- never calls SampleDataPopulator.clear(), which
 * unconditionally wipes users/departments/documents/notifications with no
 * scoping to sample data. A DB with any real data (or a prod DB) is a
 * permanent no-op for this bean.
 */
@Slf4j
@Component
@RequiredArgsConstructor
public class SampleDataStartupSeeder implements CommandLineRunner {

    private final UserRepository userRepository;
    private final SampleDataPopulator populator;

    @Override
    public void run(String... args) {
        if (userRepository.count() > 0) {
            return;
        }
        log.info("Users table is empty -- seeding sample data on startup (#224).");
        populator.insert();
    }
}
