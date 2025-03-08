import simpy
import random
import statistics


wait_times = []


class AirportSecurity(object):
    # assume 4 lanes with 1 resource from each type
    def __init__(self, env, num_lanes=4):
        self.env = env
        # no shared resources between lanes
        self.lanes = [
            {
                "officer": simpy.Resource(env, capacity=1),
                "baggage_screener": simpy.Resource(env, capacity=1),
                "body_screener": simpy.Resource(env, capacity=1)
            }
            for _ in range(num_lanes)
        ]

    def check_boarding_pass(self, passenger):
        # 20-40 secs
        yield self.env.timeout(random.uniform(0.3, 0.7))

    def scan_baggage(self, passenger):
        # 2-3 mins
        yield self.env.timeout(random.uniform(2, 3))

    def scan_body(self, passenger):
        # 30-60 secs
        yield self.env.timeout(random.uniform(0.5, 1))


def choose_dynamic_lane(security):
    """
    choose the lane with the smallest combined effective load across all three stages.
    for each lane, the effective load for a stage is calculated as:
      - length of the resource queue
      + 1 if the resource is currently busy.
    the total load is the sum for the officer, baggage screener, and body screener.
    """
    best_lane = None
    best_lane_index = -1
    best_load = float('inf')

    for lane_index, lane in enumerate(security.lanes):
        total_load = 0
        for resource_name in ["officer", "baggage_screener", "body_screener"]:
            resource = lane[resource_name]
            effective_load = len(resource.queue)
            if resource.count >= resource.capacity:
                effective_load += 1
            total_load += effective_load

        if total_load < best_load:
            best_load = total_load
            best_lane = lane
            best_lane_index = lane_index
    return best_lane, best_lane_index


def check_passenger(env, name, security, assigned_lane=None, assigned_lane_index=None):
    arrival_time = env.now
    # if an assigned lane is provided, use it; otherwise, choose one at random.
    if assigned_lane is None:
        lane, assigned_lane_index = choose_dynamic_lane(security)
    else:
        lane = assigned_lane
    print(f"{name} assigned to lane {assigned_lane_index} at time {env.now:.2f}")

    # step 1: Boarding pass check
    with lane["officer"].request() as req:
        yield req
        yield env.process(security.check_boarding_pass(name))

    # step 2: Baggage screening
    with lane["baggage_screener"].request() as req:
        yield req
        yield env.process(security.scan_baggage(name))

    # step 3: Body screening
    with lane["body_screener"].request() as req:
        yield req
        yield env.process(security.scan_body(name))

    wait_times.append(env.now - arrival_time)
    print(f"{name} finished at time {env.now:.2f} (Total time in system: {wait_times[-1]:.2f} minutes)")


def get_mean_interarrival_time(current_time):
    """
    returns the mean interarrival time based on the current simulation time.
    - first 15 minutes: non-peak (1 minute on average)
    - 15 to 45 minutes: peak (0.5 minutes on average)
    - after 45 minutes: non-peak (1 minute on average)
    """
    if current_time < 10:
        return 1.0
    elif current_time < 50:
        return 0.5
    else:
        return 1.0


def passenger_arrivals(env, security):
    i = 0
    while True:
        # determine the mean interarrival time based on current time.
        mean_interarrival = get_mean_interarrival_time(env.now)
        # generate a new passenger after a interarrival time modeled after a Poisson distribution with a time-varying rate
        yield env.timeout(random.expovariate(1.0 / mean_interarrival))
        i += 1
        env.process(check_passenger(env, f"Passenger {i}", security))


def run_airport(running_time, num_lanes):
    env = simpy.Environment()
    security = AirportSecurity(env, num_lanes=num_lanes)

    # pre-populate each lane with a few initial passengers (e.g. 2 passengers)
    for lane_index, lane in enumerate(security.lanes):
        for j in range(2):
            env.process(
                check_passenger(
                    env,
                    f"Initial Passenger Lane {lane_index + 1}-{j + 1}",
                    security,
                    assigned_lane=lane,
                    assigned_lane_index=lane_index
                )
            )

    # average arrival rate of 2 passengers/min (decrease value to increase average)
    env.process(passenger_arrivals(env, security))
    env.run(until=running_time)


def calculate_wait_time():
    average_wait = statistics.mean(wait_times)
    minutes, frac_minutes = divmod(average_wait, 1)
    seconds = frac_minutes * 60
    return round(minutes), round(seconds)


def main():
    # run simulation for 60 minutes
    run_airport(60, 4)

    mins, secs = calculate_wait_time()
    print(
      f"\nThe average wait time is {mins} minutes and {secs} seconds.",
    )


if __name__ == "__main__":
    main()
