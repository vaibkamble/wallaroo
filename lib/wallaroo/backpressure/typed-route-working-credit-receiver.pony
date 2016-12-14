use "wallaroo/invariant"

class TypedRouteWorkingCreditReceiver[In: Any val]
  let _route: TypedRoute[In]
  let _step_type: String

  new create(tr: TypedRoute[In], step_type: String) =>
    _route = tr
    _step_type = step_type

  fun ref receive_credits(credits: ISize) =>
    ifdef debug then
      Invariant(credits > 0)
    end

    _route._close_outstanding_request()
    let credits_recouped =
      if (_route.credits_available() + credits) > _route.max_credits() then
        _route.max_credits() - _route.credits_available()
      else
        credits
      end
    _route._recoup_credits(credits_recouped)
    if credits > credits_recouped then
      _route._return_credits(credits - credits_recouped)
    end

    ifdef "credit_trace" then
      @printf[I32]("--Route (%s): rcvd %llu credits. Used %llu. Had %llu out of %llu.\n".cstring(),
        _step_type.cstring(), credits, credits_recouped,
        _route.credits_available() - credits_recouped,
        _route.max_credits())
    end

    if _route.credits_available() > 0 then
      if (_route.credits_available() - credits_recouped) == 0 then
        _route._credits_replenished()
      end

      _route._update_request_more_credits_after(_route.credits_available() -
        (_route.credits_available() >> 2))
    else
      _route.request_credits()
    end
