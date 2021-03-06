# include root makefile
ifndef ROOT_MAKEFILE_MK
include ../../Makefile
endif

# prevent rules from being evaluated/included multiple times
ifndef $(abspath $(lastword $(MAKEFILE_LIST)))_MK
$(abspath $(lastword $(MAKEFILE_LIST)))_MK := 1


# The following are control variables that determine what logic from `rules.mk` is enabled

# `true`/`false` to enable/disable the actual unit test command so it can be overridden (the targets are still created)
# applies to both the pony and elixir test targets
$(abspath $(lastword $(MAKEFILE_LIST)))_UNIT_TEST_COMMAND := false

# `true`/`false` to enable/disable generate pony related targets (build/test/clean) for pony sources in this directory
# otherwise targets only get created if there are pony sources (*.pony) in this directory.
$(abspath $(lastword $(MAKEFILE_LIST)))_PONY_TARGET := false

# `true`/`false` to enable/disable generate final file build target using ponyc command for the pony build target so
# it can be overridden manually
$(abspath $(lastword $(MAKEFILE_LIST)))_PONYC_TARGET := false

# `true`/`false` to enable/disable generate exs related targets (build/test/clean) for elixir sources in this directory
# otherwise targets only get created if there are elixir sources (*.exs) in this directory.
$(abspath $(lastword $(MAKEFILE_LIST)))_EXS_TARGET := false

# `true`/`false` to enable/disable generate docker related targets (build/push) for a Dockerfile in this directory
# otherwise targets only get created if there is a Dockerfile in this directory
$(abspath $(lastword $(MAKEFILE_LIST)))_DOCKER_TARGET := false

# `true`/`false` to enable/disable recursing into Makefiles of subdirectories if they exist
# (and by recursion every makefile in the tree that is referenced)
$(abspath $(lastword $(MAKEFILE_LIST)))_RECURSE_SUBMAKEFILES := false

WORD_COUNT_GO_DEMO_PATH := $(dir $(abspath $(lastword $(MAKEFILE_LIST))))
GO_PONY_LIB := $(wallaroo_path)/go_api/go
WORD_COUNT_DEMO_GOPATH := $(WORD_COUNT_GO_DEMO_PATH)/go:$(GO_PONY_LIB)

# standard rules generation makefile
include $(rules_mk_path)

build-demos-go_word_count: word_count_go_demo_build
unit-tests-demos-go_word_count: build-demos-go_word_count
clean-demos-go_word_count: word_count_go_demo_clean

word_count_go_demo_build: $(WORD_COUNT_GO_DEMO_PATH)/go_word_count

word_count_go_demo_clean:
	$(QUIET)rm -rf $(WORD_COUNT_GO_DEMO_PATH)/lib $(WORD_COUNT_GO_DEMO_PATH)/.deps $(WORD_COUNT_GO_DEMO_PATH)/go_word_count $(WORD_COUNT_GO_DEMO_PATH)/go_word_count.d

-include $(WORD_COUNT_GO_DEMO_PATH)/go_word_count.d
$(WORD_COUNT_GO_DEMO_PATH)/go_word_count: $(WORD_COUNT_GO_DEMO_PATH)/lib/libwallaroo.a
	$(call PONYC,$(abspath $(WORD_COUNT_GO_DEMO_PATH:%/=%)))

$(WORD_COUNT_GO_DEMO_PATH)/lib/libwallaroo.a: $(WORD_COUNT_GO_DEMO_PATH)/go/src/word_count/word_count.go
	$(QUIET)export GOPATH=$(WORD_COUNT_DEMO_GOPATH) && go build -buildmode=c-archive -o $(WORD_COUNT_GO_DEMO_PATH)lib/libwallaroo.a word_count

# end of prevent rules from being evaluated/included multiple times
endif
